#!/usr/bin/env python3
"""Patch the reTB server so it knows the modded characters, recodes and companions.

Two targets, same edits:

  reTB Host APK (server running on the phone):
    python3 host_mod.py --apk reTB-Host.apk --chrdb <modded ChrDatabase.json> --new-chr 1289 \
        --buddies ../server/buddies.json --out reTB-Host-mod.apk --keystore terramod.keystore

  reTB folder (server running on a PC, e.g. reTBpc or a plain reTB checkout):
    python3 host_mod.py --retb-folder C:/path/to/reTB --chrdb <modded ChrDatabase.json> --new-chr 1289 \
        --buddies ../server/buddies.json

Edits (tb_server/data): rebirth_map.json, chr_to_jobs.json, chr_names.json, chr_rarity.json,
chr_to_species.json, joblevel_exp_caps.json, patchData.zip (chrInfos + chrdata), buddydb_full.json;
(tb_server/handlers/userdata): buddy.py, buddy_consts.py, buddy_helpers.py.
APK mode then recompiles the .pyc, updates chaquopy build.json, aligns and signs.
Folder mode writes the files in place (originals kept as *.terramod-orig) and needs no signing.
"""
import argparse
import hashlib
import io
import json
import os
import struct
import subprocess
import tempfile
import zipfile

D = "tb_server/data/"
BT = os.environ.get("TERRAMOD_BT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build-tools"))


def compact(o):
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))


def patch_app(files, chrdb, new_ids, log):
    infos = {i["ID"]: i for i in chrdb["infos"]}
    jobs = {j["ID"]: j for j in chrdb["data"]}
    load = lambda n: json.loads(files[D + n].decode("utf-8"))
    rb, c2j, names = load("rebirth_map.json"), load("chr_to_jobs.json"), load("chr_names.json")
    rar, spe, caps = load("chr_rarity.json"), load("chr_to_species.json"), load("joblevel_exp_caps.json")
    pz = zipfile.ZipFile(io.BytesIO(files[D + "patchData.zip"]))
    patch = json.loads(pz.read("patchRawData.json"))
    p_infos, p_chr = patch["chrDatabase"]["chrInfos"], patch["chrDatabase"]["chrdata"]
    tmpl_entry_keys = list(p_chr[0].keys())

    for cid in new_ids:
        info = infos[cid]
        job0 = jobs[info["Jobs"][0]]
        c2j[str(cid)] = info["Jobs"]
        names[str(cid)] = info["NameString"]["en"]
        rar[str(cid)] = info["rarity"]
        spe[str(cid)] = job0["Species"]
        for jid in info["Jobs"]:
            # EXP cap: same curve as a job with identical EXPmax/EXPcoeff, else scale
            same = [k for k, j in jobs.items() if k != jid and str(k) in caps
                    and j["EXPmax"] == jobs[jid]["EXPmax"] and j["EXPcoeff"] == jobs[jid]["EXPcoeff"]]
            if not same:
                raise SystemExit(f"no EXP-cap reference for job {jid}")
            caps[str(jid)] = caps[str(same[0])]
        for r in chrdb["rebirthInfo"]:
            if r["dstChrID"] == cid:
                rb[str(r["ID"])] = {"coins": r["coins"], "dst": cid,
                                    "items": [[c["code"] // 256, c["code"] % 256] for c in r["items"]],
                                    "mons": [[m["chrID"], m["level"]] for m in r["mons"]], "src": r["srcChrID"]}
                log.append(f"server: recode #{r['ID']} {r['srcChrID']} -> {cid}")
        if not any(x["chrID"] == cid for x in p_infos):
            p_infos.append({"chrID": cid, "rarity": info["rarity"], "kind": info["kind"],
                            "chrType": info["chrType"], "inEvent": bool(info["inEvent"]),
                            "generation": info["generation"], "Jobs": info["Jobs"]})
        if not any(x["chrID"] == cid for x in p_chr):
            e = {}
            for k in tmpl_entry_keys:
                if k == "chrID":
                    e[k] = cid
                elif k == "name":
                    e[k] = info["NameString"]["en"]
                else:
                    e[k] = job0[k]
            p_chr.append(e)
        log.append(f"server: character {cid} {info['NameString']['en']} jobs={info['Jobs']}")

    # The client applies patch chrInfos BY INDEX onto ChrDatabase.infos (sorted by ID),
    # so entry i must describe infos[i]; otherwise it would overwrite another character.
    base_ids = [i["ID"] for i in chrdb["infos"]]
    if [x["chrID"] for x in p_infos] != base_ids[:len(p_infos)]:
        raise SystemExit("patch chrInfos no longer index-aligned with ChrDatabase.infos")

    files[D + "rebirth_map.json"] = json.dumps(rb, ensure_ascii=False).encode()
    for n, o in (("chr_to_jobs.json", c2j), ("chr_names.json", names), ("chr_rarity.json", rar),
                 ("chr_to_species.json", spe), ("joblevel_exp_caps.json", caps)):
        files[D + n] = json.dumps(o, ensure_ascii=False, indent=2).encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as out:
        out.writestr(pz.infolist()[0], compact(patch).encode())
    files[D + "patchData.zip"] = buf.getvalue()


UH = "tb_server/handlers/userdata/"
TERRAMOD_TAG = "# --- TerraMod custom companions ---"


def _replace_once(src, old, new, name):
    if src.count(old) != 1:
        raise SystemExit(f"server code patch: anchor not found exactly once in {name}: {old[:60]!r}")
    return src.replace(old, new)


def patch_buddies(files, buddies, log):
    """Server side of custom companions: master data + unique / locked behaviour.

    buddies: list of dicts {id, rarity_letter, name{...}, pool: "truth"|"fellowship"|None, unique: bool}.
    """
    if not buddies:
        return
    load = lambda n: json.loads(files[D + n].decode("utf-8"))
    db = load("buddydb_full.json")
    have = {b["buddy_id"] for b in db["data"]}
    for b in buddies:
        if b["id"] in have:
            continue
        db["data"].append({"buddy_id": b["id"], "name": b["name"], "rarity": b["rarity_letter"],
                           "max_level": b["max_level"], "exp_max": b["exp_max"], "base_exp": b["base_exp"],
                           "base_coin": b["base_coin"], "exp_coeff": b["exp_coeff"], "evolve_id": b["evolve_id"],
                           "coins_to_evolve": b["coins_to_evolve"], "items": [0, 0, 0],
                           "same_bonus_bias": b["same_bonus_bias"]})
        log.append(f"server: buddy {b['id']} {b['name']['en']} ({b['rarity_letter']})")
    db["data"].sort(key=lambda x: x["buddy_id"])
    files[D + "buddydb_full.json"] = json.dumps(db, ensure_ascii=False, indent=2).encode()

    uniq = sorted(b["id"] for b in buddies if b.get("unique"))
    truth = sorted(b["id"] for b in buddies if b.get("pool") == "truth")
    fell = sorted(b["id"] for b in buddies if b.get("pool") == "fellowship")
    c = files[UH + "buddy_consts.py"].decode("utf-8")
    if TERRAMOD_TAG not in c:
        c += (f"\n\n{TERRAMOD_TAG}\n"
              f"# Unique companions: at most one copy, delivered locked, never sold or fed.\n"
              f"UNIQUE_BUDDY_IDS = frozenset({uniq!r})\n"
              f"BUDDY_TRUTH_IDS = BUDDY_TRUTH_IDS + {truth!r}\n"
              f"BUDDY_FELLOWSHIP_IDS = BUDDY_FELLOWSHIP_IDS + {fell!r}\n")
        files[UH + "buddy_consts.py"] = c.encode()

    guarantee = {b["id"]: b["after_chr"] for b in buddies if b.get("after_chr")}
    h = files[UH + "buddy_helpers.py"].decode("utf-8")
    if TERRAMOD_TAG not in h:
        h += f"""

{TERRAMOD_TAG}
from tb_server.handlers.userdata.buddy_consts import UNIQUE_BUDDY_IDS  # noqa: E402

BUDDY_LOCK_FLAG = 2   # client Buddy flag bit: locked (cannot be sold / used as material)


def owned_buddy_ids() -> "set[int]":
    return {{int(entry.buddyID or entry.bid or 0) for entry in active_session().buddyInfo}}


def unique_filtered_pool(pool: "list[int]", taken: "Iterable[int]" = ()) -> "list[int]":
    \"\"\"Drop unique companions the player already owns (or just drew) from a pool.\"\"\"
    blocked = (owned_buddy_ids() | set(taken)) & UNIQUE_BUDDY_IDS
    return [bid for bid in pool if bid not in blocked]


_terramod_new_buddy_entry = new_buddy_entry
_terramod_draw_buddies = draw_buddies
_terramod_build_buddy_slot_list = build_buddy_slot_list


def new_buddy_entry(buddy_id: int) -> BuddyInfoEntry:  # noqa: F811
    entry = _terramod_new_buddy_entry(buddy_id)
    if buddy_id in UNIQUE_BUDDY_IDS:
        entry.flag = int(entry.flag or 0) | BUDDY_LOCK_FLAG
    return entry


def draw_buddies(pool, rates, count=1):  # noqa: F811
    drawn: "list[int]" = []
    for _ in range(max(1, count)):
        live = unique_filtered_pool(pool, drawn)
        drawn.extend(_terramod_draw_buddies(live, rates, 1))
    return drawn


def build_buddy_slot_list(pool, rates):  # noqa: F811
    return _terramod_build_buddy_slot_list(unique_filtered_pool(pool), rates)


# Companions guaranteed on the first coin (Fellowship) draw once the player owns a character.
GUARANTEE_AFTER_CHR = {guarantee!r}   # buddy_id -> chrID


def terramod_guaranteed(is_truth: bool, entries: "list[BuddyInfoEntry]") -> "list[BuddyInfoEntry]":
    if is_truth or not entries:
        return entries
    roster = {{int(getattr(c, "id", 0) or 0) for c in (active_session().chrdata or [])}}
    owned = owned_buddy_ids()
    for bid, cid in GUARANTEE_AFTER_CHR.items():
        if cid in roster and bid not in owned and all(int(e.buddyID or 0) != bid for e in entries):
            entries[0] = new_buddy_entry(bid)
            break
    return entries
"""
        files[UH + "buddy_helpers.py"] = h.encode()

    m = files[UH + "buddy.py"].decode("utf-8")
    if TERRAMOD_TAG not in m:
        m = _replace_once(m, "from fastapi import Request\n",
                          "from fastapi import Request\n\n" + TERRAMOD_TAG +
                          "\nfrom tb_server.handlers.userdata.buddy_consts import UNIQUE_BUDDY_IDS\n"
                          "from tb_server.handlers.userdata.buddy_helpers import terramod_guaranteed\n", "buddy.py")
        m = _replace_once(m, "                   for bid in draw_buddies(pool, rates, count)]\n",
                          "                   for bid in draw_buddies(pool, rates, count)]\n"
                          "    new_entries = terramod_guaranteed(is_truth, new_entries)\n", "buddy.py")
        m = _replace_once(m, "    sold_entries = [entry for entry in roster if int(entry.iid) in sell_iids]\n",
                          "    sold_entries = [entry for entry in roster if int(entry.iid) in sell_iids\n"
                          "                    and int(entry.buddyID or entry.bid or 0) not in UNIQUE_BUDDY_IDS]\n",
                          "buddy.py")
        m = _replace_once(m, "    base_level = int(base.lv)\n    if base_level >= base_buddy.max_level:\n",
                          "    if any(int(mat.buddyID or mat.bid or 0) in UNIQUE_BUDDY_IDS for mat in materials):\n"
                          "        logger.info(\"buddy_strengthen: unique companion offered as material -- rejected\")\n"
                          "        return strengthen_reject(BUDDY_STRENGTHEN_INVALID_MATERIAL_ID)\n\n"
                          "    base_level = int(base.lv)\n    if base_level >= base_buddy.max_level:\n", "buddy.py")
        files[UH + "buddy.py"] = m.encode()
    log.append(f"server: unique companions {uniq}, truth pool +{truth}, fellowship pool +{fell}, "
               f"guaranteed on next coin draw {guarantee}")


def compile_pyc(files, changed, log):
    """Recompile .pyc for changed .py (same header style as the shipped ones: timestamp pyc)."""
    import importlib.util
    import marshal
    for n in sorted(changed):
        if not n.endswith(".py") or (n + "c") not in files:
            continue
        old = files[n + "c"]
        magic, flags, mtime, _size = struct.unpack("<4sIII", old[:16])
        if magic != importlib.util.MAGIC_NUMBER:
            raise SystemExit(f"host Python bytecode magic differs from ours for {n}")
        src = files[n]
        code = compile(src, n.rsplit("/", 1)[-1], "exec", dont_inherit=True, optimize=0)
        files[n + "c"] = magic + struct.pack("<III", flags, mtime, len(src)) + marshal.dumps(code)
        log.append(f"server: recompiled {n}c")


def rebuild_zip(src_zip: zipfile.ZipFile, replace: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as out:
        for it in src_zip.infolist():
            data = replace.get(it.filename, None)
            if data is None:
                data = src_zip.read(it.filename)
            zi = zipfile.ZipInfo(it.filename, it.date_time)
            zi.compress_type = it.compress_type
            zi.external_attr = it.external_attr
            out.writestr(zi, data)
    return buf.getvalue()


def write_aligned(entries, path):
    """entries: list of (ZipInfo-like, data). .so stored -> 16384, other stored -> 4."""
    import zlib
    with open(path, "wb") as f:
        central = []
        for name, ctype, data, date_time, ext_attr in entries:
            crc = zlib.crc32(data)
            if ctype == zipfile.ZIP_DEFLATED:
                co = zlib.compressobj(9, zlib.DEFLATED, -15)
                comp = co.compress(data) + co.flush()
            else:
                comp = data
            nb = name.encode()
            off = f.tell()
            align = 16384 if (ctype == 0 and name.endswith(".so")) else (4 if ctype == 0 else 1)
            pad = (-(off + 30 + len(nb))) % align
            y, mo, d, h, mi, s = date_time
            t, dt = (h << 11) | (mi << 5) | (s // 2), ((max(y, 1980) - 1980) << 9) | (mo << 5) | d
            f.write(struct.pack("<4s5H3I2H", b"PK\x03\x04", 20, 0x800, ctype, t, dt, crc, len(comp), len(data),
                                len(nb), pad) + nb + b"\0" * pad + comp)
            central.append((nb, ctype, t, dt, crc, len(comp), len(data), ext_attr, off))
        cd = f.tell()
        for nb, ctype, t, dt, crc, cl, ul, ea, off in central:
            f.write(struct.pack("<4s6H3I5H2I", b"PK\x01\x02", 20, 20, 0x800, ctype, t, dt, crc, cl, ul, len(nb),
                                0, 0, 0, 0, ea, off) + nb)
        end = f.tell()
        f.write(struct.pack("<4s4H2IH", b"PK\x05\x06", 0, 0, len(central), len(central), end - cd, cd, 0))


ORIG_SUFFIX = ".terramod-orig"


def find_tb_servers(folder):
    """Every tb_server package under a reTB folder that the server may import:
    the source tree and any installed copy inside a virtualenv (reTBpc installs one)."""
    folder = os.path.abspath(folder)
    found = []
    for root, dirs, _files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules", "build", "tests")]
        if os.path.basename(root) == "tb_server" and os.path.isfile(os.path.join(root, "data", "rebirth_map.json")):
            found.append(root)
            dirs[:] = []
    return sorted(found)


def edit(files, a, log):
    chrdb = json.load(open(a.chrdb, encoding="utf-8"))
    patch_app(files, chrdb, a.new_chr, log)
    if a.buddies:
        patch_buddies(files, json.load(open(a.buddies, encoding="utf-8")), log)


def patch_folder(a, log):
    servers = find_tb_servers(a.retb_folder)
    if not servers:
        raise SystemExit(f"no tb_server package (with data/rebirth_map.json) found under {a.retb_folder}")
    for srv in servers:
        base = os.path.dirname(srv)
        files = {}
        for sub in ("data", os.path.join("handlers", "userdata")):
            for fn in os.listdir(os.path.join(srv, sub)):
                if fn.endswith((".json", ".zip", ".py")):
                    path = os.path.join(srv, sub, fn)
                    # always start from the pristine original, so re-running with new specs is safe
                    src = path + ORIG_SUFFIX if os.path.exists(path + ORIG_SUFFIX) else path
                    files["tb_server/" + os.path.relpath(path, srv).replace(os.sep, "/")] = open(src, "rb").read()
        before = dict(files)
        sub_log = []
        edit(files, a, sub_log)
        changed = sorted(k for k, v in files.items() if before[k] != v)
        for k in changed:
            path = os.path.join(base, *k.split("/"))
            if not os.path.exists(path + ORIG_SUFFIX):
                with open(path, "rb") as fsrc, open(path + ORIG_SUFFIX, "wb") as fdst:
                    fdst.write(fsrc.read())
            with open(path, "wb") as f:
                f.write(files[k])
            cache = os.path.join(os.path.dirname(path), "__pycache__")
            if k.endswith(".py") and os.path.isdir(cache):
                stem = os.path.basename(path)[:-3] + "."
                for c in os.listdir(cache):
                    if c.startswith(stem) and c.endswith(".pyc"):
                        os.remove(os.path.join(cache, c))  # stale bytecode; Python rebuilds it
        if not log:
            log.extend(sub_log)
        log.append(f"patched {len(changed)} file(s) in {srv}")
    if any(os.sep + "site-packages" + os.sep in s + os.sep for s in servers):
        log.append("note: an installed copy (site-packages) was patched too. A server update/reinstall "
                   "replaces it - run this command again afterwards.")
    log.append("restart the server to load the changes; originals are kept next to each file as *" + ORIG_SUFFIX)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    tgt = ap.add_mutually_exclusive_group(required=True)
    tgt.add_argument("--apk", help="reTB Host APK to patch (server on the phone)")
    tgt.add_argument("--retb-folder", help="reTB folder to patch in place (server on a PC, e.g. reTBpc's reTB folder)")
    ap.add_argument("--chrdb", required=True)
    ap.add_argument("--new-chr", type=int, nargs="+", required=True)
    ap.add_argument("--out", help="output APK (APK mode)")
    ap.add_argument("--keystore", help="signing keystore (APK mode; created if missing)")
    ap.add_argument("--buddies", help="JSON list of custom companions for the server (see patch_buddies)")
    a = ap.parse_args()
    log = []
    if a.retb_folder:
        patch_folder(a, log)
        print("\n".join(log))
        return
    if not (a.out and a.keystore):
        ap.error("--apk needs --out and --keystore")
    host = zipfile.ZipFile(a.apk)
    app = zipfile.ZipFile(io.BytesIO(host.read("assets/chaquopy/app.imy")))
    files = {}
    for n in app.namelist():
        if n.startswith("tb_server/"):
            files[n] = app.read(n)
    before = dict(files)
    edit(files, a, log)
    changed = {k for k, v in files.items() if before.get(k) != v}
    compile_pyc(files, changed, log)
    changed = {k: v for k, v in files.items() if before.get(k) != v}
    new_app = rebuild_zip(app, changed)
    bj = json.loads(host.read("assets/chaquopy/build.json"))
    bj["assets"]["app.imy"] = hashlib.sha1(new_app).hexdigest()
    new_bj = json.dumps(bj, indent=4).encode()
    entries = []
    for it in host.infolist():
        if it.filename.startswith("META-INF/") and it.filename.rsplit(".", 1)[-1] in ("SF", "RSA", "DSA", "EC", "MF"):
            continue
        data = {"assets/chaquopy/app.imy": new_app, "assets/chaquopy/build.json": new_bj}.get(it.filename)
        if data is None:
            data = host.read(it.filename)
        entries.append((it.filename, it.compress_type, data, it.date_time, it.external_attr))
    with tempfile.TemporaryDirectory() as td:
        unsigned = os.path.join(td, "u.apk")
        write_aligned(entries, unsigned)
        if not os.path.exists(a.keystore):
            subprocess.run(["keytool", "-genkeypair", "-keystore", a.keystore, "-alias", "terramod", "-keyalg", "RSA",
                            "-keysize", "2048", "-validity", "36500", "-storepass", "terramod", "-keypass",
                            "terramod", "-dname", "CN=TerraMod"], check=True, capture_output=True)
        subprocess.run(["java", "-jar", os.path.join(BT, "apksigner.jar"), "sign",
                        "--ks", a.keystore, "--ks-pass", "pass:terramod", "--ks-key-alias", "terramod",
                        "--key-pass", "pass:terramod", "--out", a.out, unsigned], check=True)
    r = subprocess.run(["java", "-jar", os.path.join(BT, "apksigner.jar"), "verify", "-v", a.out],
                       capture_output=True, text=True)
    log.append("apksigner verify: " + " | ".join(l for l in r.stdout.splitlines() if "Verif" in l))
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)
    print("\n".join(log))


if __name__ == "__main__":
    main()
