#!/usr/bin/env python3
"""Terra Battle modding builder.

Applies a mod spec (new characters / DNA recodes) to the game databases inside an
APK and produces a signed, aligned APK.

    python3 terra_mod.py build --apk orig.apk --base game_data/ --mod mods/ --out out.apk

The ChrDatabase / SkillData MonoBehaviours are re-encoded with mbcodec, which is
verified byte-exact against the original APK before anything is changed.
"""
import argparse
import copy
import glob
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mbcodec import encode, learn, load_tables  # noqa: E402
from unityfs import Bundle, SerializedFile  # noqa: E402

OBJECTS = {"ChrDatabase": 12688, "SkillData": 12700, "EffectSet": 12692, "BuddyDatabase": 13474}
DATA = "assets/bin/Data/data.unity3d"
META = "assets/bin/Data/Managed/Metadata/global-metadata.dat"
LANGS = ("en", "ja", "fr", "de", "es", "zh_tw")


def langs(v):
    """Accept a plain string or a partial {lang: text} dict; fill missing langs from en."""
    if isinstance(v, str):
        v = {"en": v}
    en = v.get("en", "")
    out = {}
    for l in LANGS:
        out[l] = v.get(l) or (en if l != "ja" else v.get("ja", en))
    return out


# ---------------------------------------------------------------- mod application
def apply_character(db, spec, log):
    infos = {i["ID"]: i for i in db["infos"]}
    jobs = {j["ID"]: j for j in db["data"]}
    cid = spec["id"]
    if cid in infos:
        raise ValueError(f"character ID {cid} already exists ({infos[cid]['NameString']['en']})")

    tmpl_info = infos[spec["template_character"]]
    info = copy.deepcopy(tmpl_info)
    info["ID"] = cid
    info["NameString"] = langs(spec["name"])
    info["addProfs"] = []
    for k in ("rarity", "generation", "plusType", "isLambda", "kind", "chrType", "unlockChapter", "canDrop", "sortNameJa"):
        if k in spec:
            info[k] = spec[k]
    new_jobs = []
    for n, jspec in enumerate(spec["jobs"]):
        jid = jspec["id"]
        if jid in jobs:
            raise ValueError(f"job ID {jid} already exists")
        job = copy.deepcopy(jobs[jspec.get("template_job", jobs[tmpl_info["Jobs"][0]]["ID"])])
        job["ID"] = jid
        job["chrID"] = cid
        job["NameString"] = langs(jspec.get("name", spec["name"]))
        if "profile" in jspec:
            job["ProfileString"] = langs(jspec["profile"])
        for k, v in jspec.get("fields", {}).items():
            if k not in job:
                raise KeyError(f"unknown job field {k}")
            job[k] = v
        st = jspec.get("stats")
        if st:
            for s in ("HP", "ATK", "DEF", "SATK", "SDEF"):
                if s in st:
                    lo, hi = st[s] if isinstance(st[s], list) else (round(st[s] / 10), st[s])
                    job[s] = job[s + "min"] = lo
                    job[s + "max"] = hi
        if "skills" in jspec:
            if len(jspec["skills"]) != len(job["skills"]):
                raise ValueError("skills must have exactly %d entries" % len(job["skills"]))
            job["skills"] = jspec["skills"]
        if "skill_levels" in jspec:
            job["skillMasterLevel"] = jspec["skill_levels"]
        if "image_id" in jspec:
            job["ImageID"] = jspec["image_id"]
        db["data"].append(job)
        new_jobs.append(jid)
        tmpl_jid = jspec.get("template_job", tmpl_info["Jobs"][0])
        NEW_JOBS.append((jid, tmpl_jid))
    info["Jobs"] = new_jobs
    db["infos"].append(info)
    log.append(f"+ character {cid} {info['NameString']['en']} jobs={new_jobs}")

    rc = spec.get("recode")
    if rc:
        src = rc["from"]
        if src not in infos:
            raise ValueError(f"recode source {src} not found")
        if any(r["srcChrID"] == src for r in db["rebirthInfo"]):
            raise ValueError(f"character {src} already has a DNA recode")
        rid = rc.get("id") or max(r["ID"] for r in db["rebirthInfo"]) + 1
        tmpl = copy.deepcopy(db["rebirthInfo"][0])
        tmpl.update({
            "ID": rid, "srcChrID": src, "dstChrID": cid, "coins": rc["coins"],
            "availableVersion": rc.get("availableVersion", 2.5),
            "items": [{"code": c if isinstance(c, int) else c[0] * 256 + c[1]} for c in rc["items"]],
            "mons": [{"chrID": m[0], "level": m[1]} for m in rc["mons"]],
        })
        if len(tmpl["items"]) != 3 or len(tmpl["mons"]) != 2:
            raise ValueError("recode needs exactly 3 items and 2 mons")
        db["rebirthInfo"].append(tmpl)
        info["rebirthFromID"] = src
        info["ancestorChrID"] = infos[src].get("ancestorChrID") or src
        log.append(f"+ DNA recode #{rid}: {infos[src]['NameString']['en']} -> {info['NameString']['en']}")


def apply_skill(sdb, spec, keys, log):
    """Append a new skill cloned from `template` (skills are referenced by list index)."""
    types = sdb["types"]
    sk = copy.deepcopy(types[spec["template"]])
    for k, v in spec.get("set", {}).items():
        if k not in sk or k.endswith("String"):
            raise KeyError(f"unknown/invalid skill field {k}")
        if isinstance(sk[k], float):
            v = float(v)
        sk[k] = v
    for k, fld in (("name", "nameString"), ("desc", "descString"), ("range", "rangePrefixString")):
        if k in spec:
            sk[fld] = langs(spec[k])
    # Client SkillData.GetType(id): skill ID = list index + 1, and IDs 3843..3852
    # (TMP_BASE .. TMP_BASE+9) are served from the runtime tmpTypes[10] array (null),
    # so pad those slots with inert placeholders and never hand them out.
    TMP_BASE, TMP_COUNT = 3843, 10
    while TMP_BASE - 1 <= len(types) < TMP_BASE - 1 + TMP_COUNT:
        types.append(copy.deepcopy(types[0]))
    types.append(sk)
    sid = len(types)  # ID of the skill just appended (index + 1)
    assert not (TMP_BASE <= sid < TMP_BASE + TMP_COUNT)
    keys[spec["key"]] = sid
    log.append(f"+ skill ID {sid} {sk['nameString']['en']} (from ID {spec['template'] + 1})")


BUDDY_FIELDS_DIRECT = ("SortID", "exclusiveChrID", "exclusiveSpeciesID", "rarity", "type", "attrib", "kind",
                       "RequiredLevel", "MaxLevel", "ATKmin", "DEFmin", "SATKmin", "SDEFmin", "BOOSTmin",
                       "ATKmax", "DEFmax", "SATKmax", "SDEFmax", "BOOSTmax", "EXPmax", "BaseEXP", "BaseCOIN",
                       "evolveID", "coinsToEvolve", "DropLevel", "SameBonusBias", "canDrop", "sortNameJa")


def apply_buddy(bdb, spec, keys, log):
    """Append a new companion (buddy) cloned from `template`."""
    data = bdb["data"]
    by_id = {b["ID"]: b for b in data}
    bid = spec["id"]
    if bid in by_id:
        raise ValueError(f"buddy ID {bid} already exists ({by_id[bid]['NameString']['en']})")
    b = copy.deepcopy(by_id[spec["template"]])
    b["ID"] = bid
    b["NameString"] = langs(spec["name"])
    if "desc" in spec:
        b["DescString"] = langs(spec["desc"])
    for k in BUDDY_FIELDS_DIRECT:
        if k in spec:
            b[k] = spec[k]
    if "image_id" in spec:
        b["ImageID"] = spec["image_id"]
    if "skill" in spec:
        sk = spec["skill"]
        b["skill"] = keys[sk[1:]] if isinstance(sk, str) and sk.startswith("@") else sk
    data.append(b)
    log.append(f"+ buddy {bid} {b['NameString']['en']} (skill #{b['skill']}, image {b['ImageID']})")


def resolve_skill_refs(ch, keys):
    for j in ch.get("jobs", []):
        if "skills" in j:
            j["skills"] = [keys[s[1:]] if isinstance(s, str) and s.startswith("@") else s for s in j["skills"]]


NEW_JOBS = []


def finalize(dbs, log):
    """Keep tables sorted like the originals, add per-job UI offsets, recompute job hashes."""
    from jobhash import job_hash
    salt = "mist_guardians_keycode"
    chr_db = dbs["ChrDatabase"]
    chr_db["data"].sort(key=lambda j: j["ID"])
    chr_db["infos"].sort(key=lambda i: i["ID"])
    chr_db["rebirthInfo"].sort(key=lambda r: r["ID"])
    # (mustache-event offsets in EffectSet are optional per job; new jobs use the game default)
    fixed = 0
    for j in chr_db["data"]:
        h = job_hash(j, salt)
        if h != j["hash"]:
            j["hash"] = h
            fixed += 1
    log.append(f"sorted tables, recomputed {fixed} job hash(es)")
    if "BuddyDatabase" in dbs:
        from buddyhash import buddy_hash
        bd = dbs["BuddyDatabase"]["data"]
        bd.sort(key=lambda b: b["ID"])
        n = 0
        for b in bd:
            h = buddy_hash(b, salt)
            if h != b["hash"]:
                b["hash"] = h
                n += 1
        log.append(f"recomputed {n} buddy hash(es)")


def apply_mods(dbs, mod_dir, log):
    for path in sorted(glob.glob(os.path.join(mod_dir, "*.json"))):
        spec = json.load(open(path, encoding="utf-8"))
        log.append(f"[{os.path.basename(path)}]")
        keys = {}
        for sk in spec.get("skills", []):
            apply_skill(dbs["SkillData"], sk, keys, log)
        for bd in spec.get("buddies", []):
            apply_buddy(dbs["BuddyDatabase"], bd, keys, log)
        for ch in spec.get("characters", []):
            resolve_skill_refs(ch, keys)
            apply_character(dbs["ChrDatabase"], ch, log)


# ---------------------------------------------------------------- APK packaging
def align_zip(src, dst, align=4):
    """zipalign: pad local headers so STORED entries start on `align` boundaries."""
    with zipfile.ZipFile(src) as zin, open(dst, "wb") as out:
        central = []
        for info in zin.infolist():
            data = zin.open(info).read() if False else None
            raw = zin.fp
            raw.seek(info.header_offset)
            hdr = raw.read(30)
            nlen, xlen = struct.unpack_from("<HH", hdr, 26)
            name = raw.read(nlen)
            raw.read(xlen)
            comp = raw.read(info.compress_size)
            offset = out.tell()
            extra = b""
            if info.compress_type == zipfile.ZIP_STORED:
                pad = (align - (offset + 30 + nlen) % align) % align
                extra = b"\0" * pad
            flags = struct.unpack_from("<H", hdr, 6)[0] & ~0x8  # no data descriptor
            out.write(struct.pack("<4s5H3I2H", b"PK\x03\x04", 20 if info.compress_type == 0 else 20, flags,
                                  info.compress_type, *_dos(info), info.CRC, info.compress_size,
                                  info.file_size, nlen, len(extra)) + name + extra + comp)
            central.append((info, name, offset, flags))
        cd_start = out.tell()
        for info, name, offset, flags in central:
            out.write(struct.pack("<4s6H3I5H2I", b"PK\x01\x02", 20, 20, flags, info.compress_type, *_dos(info),
                                  info.CRC, info.compress_size, info.file_size, len(name), 0, 0, 0, 0,
                                  info.external_attr, offset) + name)
        cd_end = out.tell()
        out.write(struct.pack("<4s4H2IH", b"PK\x05\x06", 0, 0, len(central), len(central),
                              cd_end - cd_start, cd_start, 0))


def _dos(info):
    y, mo, d, h, mi, s = info.date_time
    return ((h << 11) | (mi << 5) | (s // 2), ((max(y, 1980) - 1980) << 9) | (mo << 5) | d)


BT = os.environ.get("TERRAMOD_BT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build-tools"))


def sign(apk_in, apk_out, keystore, alias="terramod", password="terramod"):
    """zipalign (-p: page-align .so) + official apksigner (v1+v2)."""
    if not os.path.exists(keystore):
        subprocess.run(["keytool", "-genkeypair", "-keystore", keystore, "-alias", alias, "-keyalg", "RSA",
                        "-keysize", "2048", "-validity", "36500", "-storepass", password, "-keypass", password,
                        "-dname", "CN=TerraMod"], check=True, capture_output=True)
    aligned = apk_out + ".aligned"
    env = dict(os.environ, LD_LIBRARY_PATH=os.path.join(BT, "lib64"))
    subprocess.run([os.path.join(BT, "zipalign"), "-f", "-p", "4", apk_in, aligned], check=True, env=env,
                   capture_output=True)
    subprocess.run(["java", "-jar", os.path.join(BT, "apksigner.jar"), "sign", "--ks", keystore,
                    "--ks-pass", "pass:" + password, "--ks-key-alias", alias, "--key-pass", "pass:" + password,
                    "--out", apk_out, aligned], check=True, capture_output=True)
    os.remove(aligned)
    r = subprocess.run(["java", "-jar", os.path.join(BT, "apksigner.jar"), "verify", apk_out],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("apksigner verify failed: " + r.stdout + r.stderr)


ASSET_DB_PATHID = 12686  # placeholder, resolved by name below


def patch_asset_db(sf, mod_dir, log):
    """Add new images to the built-in AssetVersions TextAsset (Pieces/Illusts: id,h,name,w,ver).
    The client only downloads/loads images listed here."""
    import struct as st
    target = None
    for pid, ob in sf.objects.items():
        if ob["class"] != 49:
            continue
        od = sf.get(pid)
        (n,) = st.unpack_from("<i", od, 0)
        if od[4:4 + n] == b"AssetVersions":
            target = (pid, od, n)
            break
    if target is None:
        raise SystemExit("AssetVersions TextAsset not found")
    pid, od, n = target
    o = (4 + n + 3) & ~3
    (L,) = st.unpack_from("<i", od, o)
    body = od[o + 4:o + 4 + L].decode("ascii")
    tail = od[(o + 4 + L + 3) & ~3:]
    changed = False
    for path in sorted(glob.glob(os.path.join(mod_dir, "*.json"))):
        spec = json.load(open(path, encoding="utf-8"))
        for cat, entries in spec.get("asset_db", {}).items():
            key = f'"{cat}":['
            i = body.index(key)
            j = body.index("]", i)
            existing = json.loads(body[i + len(key) - 1:j + 1])
            ids = {(e["id"], e.get("name", "")) for e in existing}
            add = ""
            for e in entries:
                key2 = (e["id"], e.get("name", ""))
                if key2 in ids:
                    continue
                add += "," + json.dumps({"id": e["id"], "h": e["h"], "name": e.get("name", ""), "w": e["w"],
                                         "ver": e["ver"]}, separators=(",", ":"), ensure_ascii=True)
                log.append(f"asset db: {cat} {e.get('name') or 'id=' + str(e['id'])} {e['w']}x{e['h']} ver={e['ver']}")
            if add:
                body = body[:j] + add + body[j:]
                changed = True
    if not changed:
        return False
    json.loads(body)  # must stay valid JSON
    nb = body.encode("ascii")
    new = od[:o] + st.pack("<i", len(nb)) + nb + b"\0" * ((-len(nb)) % 4) + tail
    sf.replace(pid, new)
    return True


def bump_asset_versions(xml: bytes, mod_dir, log) -> bytes:
    """Force re-download of modded images: set <Piece>/<illust> versions from mod specs."""
    import re
    txt = xml.decode("us-ascii")
    for path in sorted(glob.glob(os.path.join(mod_dir, "*.json"))):
        spec = json.load(open(path, encoding="utf-8"))
        for tag, close in (("Piece", "</Pieces>"), ("illust", "</Illusts>")):
            for iid, ver in spec.get("asset_versions", {}).get(tag, {}).items():
                pat = re.compile(rf"(<{tag}>\s*<id>{int(iid)}</id>\s*<version>)\d+(</version>)")
                if pat.search(txt):
                    txt = pat.sub(rf"\g<1>{int(ver)}\g<2>", txt)
                else:
                    entry = (f"  <{tag}>\n      <id>{int(iid)}</id>\n      <version>{int(ver)}</version>\n"
                             f"    </{tag}>\n  ")
                    i = txt.index(close)
                    txt = txt[:i] + entry + txt[i:]
                log.append(f"asset version: {tag} {iid} -> v{ver}")
    return txt.encode("us-ascii")


def build(args):
    log = []
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with zipfile.ZipFile(args.apk) as z:
        meta = z.read(META)
        bundle_raw = z.read(DATA)
    inv, fwd = load_tables(meta)
    bundle = Bundle(bundle_raw)
    sf = SerializedFile(bundle.files["resources.assets"][0])

    dbs, schemas, headers = {}, {}, {}
    for name, pid in OBJECTS.items():
        raw = sf.get(pid)
        data = json.load(open(os.path.join(args.base, name + ".json"), encoding="utf-8"))
        schemas[name] = learn(raw, data, inv)
        headers[name] = raw[:32]
        if encode(data, schemas[name], headers[name], fwd) != raw:
            raise SystemExit(f"{name}: base JSON does not round-trip against this APK - aborting")
        dbs[name] = data
    log.append("round-trip check OK (" + ", ".join(OBJECTS) + ")")

    original = copy.deepcopy(dbs)
    from jobhash import job_hash
    bad = [j["ID"] for j in dbs["ChrDatabase"]["data"] if job_hash(j, "mist_guardians_keycode") != j["hash"]]
    if bad:
        raise SystemExit(f"job hash formula mismatch on original data: {bad[:5]}")
    from buddyhash import buddy_hash
    if any(buddy_hash(b) != b["hash"] for b in dbs["BuddyDatabase"]["data"]):
        raise SystemExit("buddy hash formula mismatch on original data")
    apply_mods(dbs, args.mod, log)
    finalize(dbs, log)

    changed = 0
    for name, pid in OBJECTS.items():
        if dbs[name] != original[name]:
            sf.replace(pid, encode(dbs[name], schemas[name], headers[name], fwd))
            changed += 1
    if patch_asset_db(sf, args.mod, log):
        changed += 1
    bundle.files["resources.assets"][0] = sf.bytes()
    new_bundle = bundle.save()

    # verify: re-open what we wrote and decode-check
    vb = Bundle(new_bundle)
    vsf = SerializedFile(vb.files["resources.assets"][0])
    for name, pid in OBJECTS.items():
        if vsf.get(pid) != encode(dbs[name], schemas[name], headers[name], fwd):
            raise SystemExit(f"verification failed for {name}")
        learn(vsf.get(pid), dbs[name], inv)  # must parse back to the modded JSON
    log.append(f"re-read verification OK ({changed} database(s) changed)")

    native = set()
    for path in sorted(glob.glob(os.path.join(args.mod, "*.json"))):
        native |= set(json.load(open(path, encoding="utf-8")).get("native", []))
    patched_so = None
    if native:
        import il2cpp_lite
        import native_patch
        with zipfile.ZipFile(args.apk) as z:
            so = z.read("lib/arm64-v8a/libil2cpp.so")
        patched_so = native_patch.patch(so, il2cpp_lite.Elf(so).v2o, sorted(native))
        log.append(f"native patches {sorted(native)} applied to arm64 libil2cpp.so; armeabi-v7a removed")

    with tempfile.TemporaryDirectory() as td:
        unsigned = os.path.join(td, "u.apk")
        with zipfile.ZipFile(args.apk) as zin, zipfile.ZipFile(unsigned, "w") as zout:
            for it in zin.infolist():
                if it.filename.startswith("META-INF/") and it.filename.rsplit(".", 1)[-1] in ("SF", "RSA", "DSA", "EC", "MF"):
                    continue
                if patched_so is not None and it.filename.startswith("lib/armeabi-v7a/"):
                    continue
                payload = new_bundle if it.filename == DATA else zin.read(it.filename)
                if patched_so is not None and it.filename == "lib/arm64-v8a/libil2cpp.so":
                    payload = patched_so
                if it.filename == "assets/AssetVersions.xml":
                    payload = bump_asset_versions(payload, args.mod, log)
                zi = zipfile.ZipInfo(it.filename, it.date_time)
                zi.compress_type = it.compress_type
                zi.external_attr = it.external_attr
                zout.writestr(zi, payload)
        sign(unsigned, args.out, args.keystore)
    if args.dump:
        os.makedirs(args.dump, exist_ok=True)
        for name in dbs:
            json.dump(dbs[name], open(os.path.join(args.dump, name + ".json"), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
    log.append(f"wrote {args.out}")
    print("\n".join(log))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--apk", required=True)
    b.add_argument("--base", required=True, help="folder with original ChrDatabase.json / SkillData.json")
    b.add_argument("--mod", required=True, help="folder with mod spec *.json files")
    b.add_argument("--out", required=True)
    b.add_argument("--keystore", default=os.path.expanduser("~/.terramod.keystore"))
    b.add_argument("--dump", help="write the modded databases here for inspection")
    a = ap.parse_args()
    if a.cmd == "build":
        build(a)


if __name__ == "__main__":
    main()
