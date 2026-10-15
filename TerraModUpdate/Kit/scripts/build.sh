#!/bin/bash
# Builds ONE APK (+ Host APK) from any set of Update folders.
#   build.sh <OUT dir> <UpdateFolder> [<UpdateFolder> ...]       e.g.  build.sh ../MacuriUpdate/out MacuriUpdate
#                                                                      build.sh ../_Combo/out MacuriUpdate KanaUpdate GugbaUpdate YapkarUpdate
# Every Update folder holds its own mods/, art/ and one native module, so any subset can be combined.
set -e
KIT="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "$KIT/.." && pwd)"
OUT="$(mkdir -p "$1" && cd "$1" && pwd)"; shift
[ $# -ge 1 ] || { echo "usage: build.sh <out dir> <UpdateFolder>..."; exit 1; }
FOLDERS=("$@")
python3 "$KIT/scripts/combine.py" check "$ROOT" "${FOLDERS[@]}"
W="$HOME/charwork"; rm -rf "$W"; mkdir -p "$W/out" "$W/bt" "$W/shim" "$W/mods" "$W/art"
cp -r "$KIT/tools" "$KIT/base" "$W/"
for f in "${FOLDERS[@]}"; do
  cp "$ROOT/$f/mods/"*.json "$W/mods/"
  [ -d "$ROOT/$f/art" ] && cp -r "$ROOT/$f/art/." "$W/art/"
done
for n in game.apk input_host.apk; do
  if [ -f "$KIT/input/$n" ]; then cp "$KIT/input/$n" "$W/$n"; else cat "$KIT/input/$n".part* > "$W/$n"; fi
done
(cd "$W" && grep -E " (game|input_host)\.apk$" "$KIT/input/SHA256.txt" | sha256sum -c -)
ln -sf "$(command -v zipalign)" "$W/bt/zipalign"
ln -sf "$(ls /usr/share/java/apksigner.jar 2>/dev/null || dpkg -L apksigner | grep 'apksigner.jar$' | head -1)" "$W/bt/apksigner.jar"
for t in llvm-mc llvm-objcopy; do
  p="$(command -v $t || ls /usr/bin/$t-* /usr/lib/llvm-*/bin/$t 2>/dev/null | head -1)"
  [ -n "$p" ] || { echo "missing $t (run setup.sh)"; exit 1; }
  ln -sf "$p" "$W/shim/$t"
done
export PATH="$W/shim:$PATH" TERRAMOD_BT="$W/bt"
cd "$W/tools"
[ -f liblz4.so ] || gcc -shared -fPIC -O2 -o liblz4.so lz4.c lz4hc.c
[ -f libetc2.so ] || { printf '#include <stdint.h>\nvoid etc2_rgba(uint32_t*a,uint64_t*b,uint32_t w,uint32_t h){}\n' > "$W/etc2.c"; gcc -shared -fPIC -o libetc2.so "$W/etc2.c"; }
cd "$W"
python3 tools/terra_mod.py build --apk game.apk --base base --mod mods --out out/TerraBattle-mod.apk --keystore tools/terramod.keystore --dump out/dump | tee out/build.log
NEW_CHR="$(python3 "$KIT/scripts/combine.py" chr_ids "$ROOT" "${FOLDERS[@]}")"
python3 "$KIT/scripts/combine.py" servers "$ROOT" out/dump/BuddyDatabase.json server_buddies.json "${FOLDERS[@]}"
H=(--apk input_host.apk --chrdb out/dump/ChrDatabase.json --new-chr $NEW_CHR --out out/reTB-Host-mod.apk --keystore tools/terramod.keystore)
[ "$(python3 -c "import json;print(len(json.load(open('server_buddies.json'))))")" != 0 ] && H+=(--buddies server_buddies.json)
python3 tools/host_mod.py "${H[@]}" | tee -a out/build.log
for a in out/TerraBattle-mod.apk out/reTB-Host-mod.apk; do java -jar bt/apksigner.jar verify -v $a | head -4; done
mkdir -p "$OUT"; rm -rf "$OUT/dump"
cp out/TerraBattle-mod.apk out/reTB-Host-mod.apk out/build.log "$OUT/"; cp -r out/dump "$OUT/dump"
mkdir -p "$OUT/gdresources_new"
for f in "${FOLDERS[@]}"; do [ -d "$ROOT/$f/gdresources_new" ] && cp -r "$ROOT/$f/gdresources_new/." "$OUT/gdresources_new/"; done
(cd "$OUT" && sha256sum *.apk | tee SHA256.txt)
echo "DONE -> $OUT   (characters: $NEW_CHR)"
