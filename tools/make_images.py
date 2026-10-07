#!/usr/bin/env python3
"""Build the downloadable image files (gdresources) for new characters / companions.

    python3 make_images.py --apk TerraBattle-mod.apk --gdres <original gdresources> \
        --recipe ../images.json --out out/gdresources

Recipe (JSON list), one entry per output file:
    {"new": "img_3001",       "template": "img_2124",    "src": "art/piece.png"}
    {"new": "illust_3001",    "template": "illust_2124", "src": "art/illust.png"}
    {"new": "buddy_521a",     "template": "buddy_513a",  "src": "art/buddy_521a.png"}
    {"new": "buddy_521b",     "template": "buddy_513b",  "src": "art/buddy_521b.png"}
    {"new": "bimg_521",       "template": "bimg_513",    "src": "art/bimg_521.png"}
    {"new": "profile_3001",   "src": "art/profile.jpg"}
    {"new": "profile_3001_m", "src": "art/profile_m.jpg", "prefix_of": "profile_3001"}

Rules (see docs/INTERNALS.md):
  * Unity bundles are rebuilt IN PLACE from an original bundle whose name has the SAME LENGTH
    (img_2124 -> img_3001). The picture is resized to the template's texture size.
  * Profile files are plain JPEGs wrapped in the game's ENCA encryption.
  * File name = md5(name + salt) + name + ".bin"; profile_X_m reuses the prefix of profile_X.
  * After shipping new files, bump the asset versions in the mod spec ("asset_db" ... "ver")
    so the client does not keep a cached old copy.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

from PIL import Image

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from assets import encrypt_enca  # noqa: E402
from assets_build import prefix_for  # noqa: E402
import assets_inplace  # noqa: E402
from mbcodec import load_tables  # noqa: E402

META = "assets/bin/Data/Managed/Metadata/global-metadata.dat"
FOLDERS = {"img_": "android/Pieces", "illust_": "android/Illust", "buddy_": "android/BuddyImages",
           "bimg_": "android/BuddyThumbs", "profile_": "Profile"}


def folder_of(name):
    for p, f in FOLDERS.items():
        if name.startswith(p):
            return f
    raise SystemExit(f"unknown asset kind: {name}")


def find_template(gdres, name):
    hits = glob.glob(os.path.join(gdres, "data_u2017", folder_of(name), "*" + name + ".bin"))
    hits = [h for h in hits if os.path.basename(h)[32:-4] == name]
    if not hits:
        raise SystemExit(f"template {name} not found under {gdres}")
    return hits[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apk", required=True, help="game APK (only global-metadata.dat is read, for the cipher table)")
    ap.add_argument("--gdres", required=True, help="original gdresources folder (templates)")
    ap.add_argument("--recipe", required=True)
    ap.add_argument("--out", required=True, help="output gdresources folder")
    a = ap.parse_args()

    inv, _ = load_tables(zipfile.ZipFile(a.apk).read(META))
    base = os.path.dirname(os.path.abspath(a.recipe))
    for e in json.load(open(a.recipe, encoding="utf-8")):
        new, src = e["new"], os.path.join(base, e["src"])
        dst_dir = os.path.join(a.out, "data_u2017", folder_of(new))
        os.makedirs(dst_dir, exist_ok=True)
        if new.startswith("profile_"):
            data = encrypt_enca(open(src, "rb").read(), inv)
            fn = prefix_for(e.get("prefix_of", new)) + new + ".bin"
        else:
            tpl = e["template"]
            data, _, fn = assets_inplace.build(find_template(a.gdres, tpl), inv, tpl, new, Image.open(src))
        open(os.path.join(dst_dir, fn), "wb").write(data)
        print(f"{folder_of(new)}/{fn}  ({len(data)} bytes)")


if __name__ == "__main__":
    main()
