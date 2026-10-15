"""Helper for build.sh.
  combine.py chr_ids  <root> <Folder>...                -> prints the chr ids of the selected Update folders
  combine.py natives  <root> <Folder>...                -> prints the native modules
  combine.py servers  <root> <dump BuddyDatabase.json> <out json> <Folder>...   -> merged server_buddies.json (names synced to the game DB)
  combine.py check    <root> <Folder>...                -> sanity checks (mod files exist, no duplicate chr ids / marks / icon slots)
"""
import json, os, sys

def meta(root, f):
    return json.load(open(os.path.join(root, f, "update.json"), encoding="utf-8"))

cmd, root = sys.argv[1], sys.argv[2]
if cmd == "chr_ids":
    print(" ".join(str(c) for f in sys.argv[3:] for c in meta(root, f)["chr_ids"]))
elif cmd == "natives":
    print(" ".join(n for f in sys.argv[3:] for n in meta(root, f)["native"]))
elif cmd == "servers":
    dump, out, folders = sys.argv[3], sys.argv[4], sys.argv[5:]
    bd = {b["ID"]: b for b in json.load(open(dump, encoding="utf-8"))["data"]}
    allsb = []
    for f in folders:
        p = os.path.join(root, f, "server_buddies.json")
        if os.path.exists(p):
            allsb += json.load(open(p, encoding="utf-8"))
    for e in allsb:
        n = bd[e["id"]]["NameString"]
        for k in ("en", "ja", "zh_tw"):
            e["name"][k] = n[k]
    json.dump(allsb, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(allsb), "server buddies")
elif cmd == "check":
    seen_chr, seen_icon = {}, {}
    for f in sys.argv[3:]:
        m = meta(root, f)
        if not os.path.isdir(os.path.join(root, f, "mods")):
            sys.exit("missing mods folder in " + f)
        for c in m["chr_ids"]:
            if c in seen_chr:
                sys.exit("character %d is in both %s and %s" % (c, seen_chr[c], f))
            seen_chr[c] = f
        for i in m.get("icons", []):
            if i in seen_icon:
                sys.exit("icon slot %d used by both %s and %s" % (i, seen_icon[i], f))
            seen_icon[i] = f
    print("ok:", ", ".join(sys.argv[3:]))
