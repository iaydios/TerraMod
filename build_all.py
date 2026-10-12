#!/usr/bin/env python3
"""One-shot build of everything a player needs - the build_all.sh steps, in Python.

    python build_all.py              # discover the inputs, build everything
    python build_all.py --dry-run    # show what would run, with which inputs

Same three steps as build_all.sh (select with --only game|server|images):

  1. game APK    tools/terra_mod.py build  -> out/TerraBattle-mod.apk (+ out/dump/)
  2. server      tools/host_mod.py         -> out/reTB-Host-mod.apk and/or a reTB
                                              folder patched in place (PC server)
  3. images      tools/make_images.py      -> out/gdresources/

Inputs are found under input/ by CONTENT, so their file names do not matter:

  game APK       a .apk holding assets/bin/Data/data.unity3d
  reTB Host APK  a .apk holding assets/chaquopy/app.imy
  reTB folder    a folder with a tb_server package inside (patched in place)
  game data      a folder with ChrDatabase/SkillData/EffectSet/BuddyDatabase .json
  gdresources    a folder with data_u2017/ inside - or a *.tar holding one,
                 unpacked once next to it and reused on later runs

Explicit flags (--game-apk --host-apk --base --gdres --retb-folder) and the
build_all.sh environment variables (GAME_APK HOST_APK BASE GDRES RETB_FOLDER
NEW_CHR KEYSTORE OUT) always override the search.

The server step needs the new character IDs; they are read from the mod specs
(characters[].id), so there is no NEW_CHR default to keep in sync. Companion
rules default to server/buddies.json, reduced to the companions the mods define.
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import tarfile
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(ROOT, "tools")
GAME_APK_MARK = "assets/bin/Data/data.unity3d"
HOST_APK_MARK = "assets/chaquopy/app.imy"
DB_JSONS = ("ChrDatabase.json", "SkillData.json", "EffectSet.json", "BuddyDatabase.json")
PRUNE = {".git", "__pycache__", "node_modules", ".venv", "venv"}
STEPS = ("game", "server", "images")


def note(msg):
    print(f"build_all: {msg}")


# ---------------------------------------------------------------- input discovery
def walk_inputs(folder):
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = sorted(d for d in dirnames if d not in PRUNE)
        yield dirpath, dirnames, filenames


def zip_marked(path, marker):
    try:
        with zipfile.ZipFile(path) as z:
            return marker in z.namelist()
    except (zipfile.BadZipFile, OSError):
        return False


def only_one(cands, what, flag):
    if len(cands) > 1:
        raise SystemExit(f"multiple candidate {what}s found:\n  " + "\n  ".join(cands) + f"\npass {flag} to choose one")
    return cands[0] if cands else None


def find_apks(input_dir):
    """Sort .apk files under input_dir by what they contain (name does not matter)."""
    game, host = [], []
    for dirpath, _dirs, files in walk_inputs(input_dir):
        for fn in files:
            if not fn.lower().endswith(".apk"):
                continue
            p = os.path.join(dirpath, fn)
            if zip_marked(p, GAME_APK_MARK):
                game.append(p)
            elif zip_marked(p, HOST_APK_MARK):
                host.append(p)
    return game, host


def find_retb_folder(input_dir):
    """Shallowest folder holding a tb_server package; deeper copies (site-packages) patch with it."""
    sys.path.insert(0, TOOLS)
    from host_mod import find_tb_servers
    servers = find_tb_servers(input_dir)
    if not servers:
        return None
    folder = os.path.dirname(min(servers, key=lambda s: (s.count(os.sep), s)))
    outside = [s for s in servers if not s.startswith(folder + os.sep)]
    if outside:
        raise SystemExit(f"multiple reTB trees under {input_dir} - pass --retb-folder")
    return folder


def find_game_data(input_dir):
    for dirpath, _dirs, files in walk_inputs(input_dir):
        if all(n in files for n in DB_JSONS):
            return dirpath
    return None


def find_gdres(input_dir, dry=False):
    """A folder holding data_u2017/, unpacking a gdresources *.tar once if that is all there is."""
    tars = []
    for dirpath, dirnames, files in walk_inputs(input_dir):
        if "data_u2017" in dirnames:
            return dirpath
        tars += [os.path.join(dirpath, f) for f in files if f.lower().endswith((".tar", ".tar.gz", ".tgz"))]
    for tar in sorted(tars):
        dst = os.path.join(input_dir, os.path.basename(tar).split(".")[0] + ".unpacked")
        if not any("data_u2017" in d for _dp, d, _f in walk_inputs(dst)):
            with tarfile.open(tar, "r:*") as t:
                if not any("data_u2017" in m.name for m in t):
                    continue
                note(f"unpacking {tar} -> {dst} (one-time)" + (" [dry-run: skipped]" if dry else ""))
                if not dry:
                    t.extractall(dst, filter="data")
        for dirpath, dirnames, _files in walk_inputs(dst):
            if "data_u2017" in dirnames:
                return dirpath
    return None


def mod_ids(mod_dir, key):
    ids = []
    for path in sorted(glob.glob(os.path.join(mod_dir, "*.json"))):
        ids += [e["id"] for e in json.load(open(path, encoding="utf-8")).get(key, [])]
    return ids


def prepare_buddies(path, known_ids, out_dir, dry=False):
    """Reduce server/buddies.json to the companions the mods define, so client and server match."""
    entries = json.load(open(path, encoding="utf-8"))
    keep = [b for b in entries if b["id"] in known_ids]
    dropped = [b["id"] for b in entries if b["id"] not in known_ids]
    if dropped:
        note(f"server buddies: ignoring {dropped} (not defined by the mods)")
    if not keep:
        return None
    if len(keep) == len(entries):
        return path
    run = os.path.join(out_dir, "server-buddies.json")
    if not dry:
        json.dump(keep, open(run, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return run


def prepare_recipe(path, out_dir, dry=False):
    """Drop image entries whose art file is missing (reported); None if nothing can be built."""
    base = os.path.dirname(os.path.abspath(path))
    entries = json.load(open(path, encoding="utf-8"))
    keep, dropped = [], []
    for e in entries:
        (keep if os.path.isfile(os.path.join(base, e["src"])) else dropped).append(e)
    for e in dropped:
        note(f"images: skipping {e['new']} - missing {e['src']}")
    if not keep:
        return None
    if dropped:  # the run recipe lives in out/, so pin the art paths
        for e in keep:
            e["src"] = os.path.join(base, e["src"])
        run = os.path.join(out_dir, "images.run.json")
        if not dry:
            json.dump(keep, open(run, "w", encoding="utf-8"), indent=1)
        return run
    return path


# ---------------------------------------------------------------- the three steps
def run_tool(name, args, dry):
    cmd = [sys.executable, os.path.join(TOOLS, name), *args]
    print(("\n[dry-run] " if dry else "\n") + "$ " + " ".join(cmd))
    if dry:
        return
    r = subprocess.run(cmd, env=dict(os.environ, PYTHONUTF8="1"))
    if r.returncode:
        raise SystemExit(f"build_all: {name} failed with exit code {r.returncode}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default="input", help="folder searched for the inputs (default: input)")
    ap.add_argument("--mod", default="mods", help="mod spec folder (default: mods)")
    ap.add_argument("--recipe", default="images.json", help="image recipe (default: images.json)")
    ap.add_argument("--buddies", help="server companion rules (default: server/buddies.json, reduced to the mods)")
    ap.add_argument("--out", default=os.environ.get("OUT", "out"))
    ap.add_argument("--keystore", default=os.environ.get("KEYSTORE", "terramod.keystore"))
    ap.add_argument("--game-apk", default=os.environ.get("GAME_APK"))
    ap.add_argument("--host-apk", default=os.environ.get("HOST_APK"))
    ap.add_argument("--base", default=os.environ.get("BASE"))
    ap.add_argument("--gdres", default=os.environ.get("GDRES"))
    ap.add_argument("--retb-folder", default=os.environ.get("RETB_FOLDER"))
    ap.add_argument("--chrdb", help="modded ChrDatabase.json for the server step (default: out/dump/ChrDatabase.json)")
    ap.add_argument("--new-chr", type=int, nargs="+", help="new character IDs (default: characters[].id in the mods)")
    ap.add_argument("--only", action="append", help="run only these step(s): game, server, images (repeatable)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan without running anything")
    a = ap.parse_args()

    os.chdir(ROOT)  # like build_all.sh: defaults and outputs are relative to the repo root
    only = {s.strip() for v in (a.only or []) for s in v.split(",") if s.strip()}
    bad = only - set(STEPS)
    if bad:
        ap.error(f"unknown --only step(s): {sorted(bad)} (choose from {', '.join(STEPS)})")
    only = only or set(STEPS)
    if not a.dry_run:
        os.makedirs(a.out, exist_ok=True)
    dump_dir = os.path.join(a.out, "dump")
    game_out = os.path.join(a.out, "TerraBattle-mod.apk")
    host_out = os.path.join(a.out, "reTB-Host-mod.apk")

    # discover (explicit --flag or environment always wins over the search; only what the
    # selected steps need is searched, so unrelated ambiguity cannot block a partial run)
    need_game_apk = "game" in only or "images" in only
    need_server, need_base, need_gdres = "server" in only, "game" in only, "images" in only
    game_apks, host_apks = find_apks(a.input) if (need_game_apk or need_server) else ([], [])
    game_apk = a.game_apk or (only_one(game_apks, "game APK", "--game-apk") if need_game_apk else None)
    host_apk = a.host_apk or (only_one(host_apks, "reTB Host APK", "--host-apk") if need_server else None)
    retb = a.retb_folder or (find_retb_folder(a.input) if need_server else None)
    base = a.base or (find_game_data(a.input) if need_base else None)
    gdres = a.gdres or (find_gdres(a.input, a.dry_run) if need_gdres else None)
    for what, val, wanted in (("game APK", game_apk, need_game_apk), ("reTB Host APK", host_apk, need_server),
                              ("reTB folder", retb, need_server), ("game data", base, need_base),
                              ("gdresources", gdres, need_gdres)):
        note(f"{what:<14} {val if val else '(not found)' if wanted else '(not searched)'}")
    if not glob.glob(os.path.join(a.mod, "*.json")):
        note(f"no mod specs in {a.mod}/ - building without content changes")

    new_chr = a.new_chr or [int(x) for x in os.environ.get("NEW_CHR", "").split()]
    new_chr = new_chr or mod_ids(a.mod, "characters")
    chrdb = a.chrdb or os.path.join(dump_dir, "ChrDatabase.json")
    skipped = []

    if "game" in only:
        missing = [n for n, v in (("game APK", game_apk), ("game data", base)) if not v]
        if missing:
            skipped.append(f"game: missing {', '.join(missing)} (game data = Terra-Tools user-data/extracted-gamedata/game_data)")
        else:
            run_tool("terra_mod.py", ["build", "--apk", game_apk, "--base", base, "--mod", a.mod,
                                      "--out", game_out, "--keystore", a.keystore, "--dump", dump_dir], a.dry_run)

    if "server" in only:
        if not (host_apk or retb):
            skipped.append("server: no reTB Host APK and no reTB folder found")
        elif not new_chr:
            skipped.append("server: no new character IDs (no characters[] in the mods; override with --new-chr)")
        elif not (a.dry_run or os.path.isfile(chrdb)):
            skipped.append(f"server: {chrdb} not found - run the game step first, or pass --chrdb")
        else:
            buddies = a.buddies
            if not buddies and os.path.isfile(os.path.join("server", "buddies.json")):
                buddies = prepare_buddies(os.path.join("server", "buddies.json"),
                                          set(mod_ids(a.mod, "buddies")), a.out, a.dry_run)
                if not buddies:
                    note("server: no companions in the mods - server/buddies.json not applied")
            common = ["--chrdb", chrdb, "--new-chr", *[str(c) for c in new_chr]]
            if buddies:
                common += ["--buddies", buddies]
            if host_apk:
                run_tool("host_mod.py", ["--apk", host_apk, "--out", host_out,
                                         "--keystore", a.keystore, *common], a.dry_run)
            if retb:
                run_tool("host_mod.py", ["--retb-folder", retb, *common], a.dry_run)
                if not a.dry_run:
                    note("restart the PC server to load the patched files")

    if "images" in only:
        recipe = None
        if not os.path.isfile(a.recipe):
            note(f"images: no recipe at {a.recipe}")
        else:
            recipe = prepare_recipe(a.recipe, a.out, a.dry_run)
        # only the cipher table (global-metadata.dat) is read, and it is identical in the
        # original APK, so this step does not depend on the game step having run
        apk = game_apk
        missing = [n for n, v in (("gdresources", gdres), ("a buildable recipe", recipe), ("game APK", apk)) if not v]
        if missing:
            skipped.append("images: missing " + ", ".join(missing))
        else:
            run_tool("make_images.py", ["--apk", apk, "--gdres", gdres, "--recipe", recipe,
                                        "--out", os.path.join(a.out, "gdresources")], a.dry_run)

    print()
    for f in (game_out, host_out, os.path.join(a.out, "gdresources")):
        if os.path.exists(f):
            note(f"done: {f}")
    if skipped:
        for s in skipped:
            note("SKIPPED " + s)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
