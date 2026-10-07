#!/bin/sh
# One-shot build of everything a player needs. Edit the paths below, then: sh build_all.sh
#
#   GAME_APK   original reTB Terra Battle APK (arm64)
#   HOST_APK   original reTBHost APK
#   BASE       folder with ChrDatabase.json / SkillData.json / EffectSet.json / BuddyDatabase.json
#              (reTBHost "extracted-gamedata/game_data", see README)
#   GDRES      your original gdresources folder (image templates)
#   NEW_CHR    IDs of the new characters defined in mods/*.json
set -e
GAME_APK=${GAME_APK:-input/TerraBattle.apk}
HOST_APK=${HOST_APK:-input/reTB-Host.apk}
BASE=${BASE:-input/game_data}
GDRES=${GDRES:-input/gdresources}
NEW_CHR=${NEW_CHR:-1289}
KEYSTORE=${KEYSTORE:-terramod.keystore}
OUT=${OUT:-out}

cd "$(dirname "$0")"
mkdir -p "$OUT"
python3 tools/terra_mod.py build --apk "$GAME_APK" --base "$BASE" --mod mods \
    --out "$OUT/TerraBattle-mod.apk" --keystore "$KEYSTORE" --dump "$OUT/dump"
python3 tools/host_mod.py --apk "$HOST_APK" --chrdb "$OUT/dump/ChrDatabase.json" --new-chr $NEW_CHR \
    --buddies server/buddies.json --out "$OUT/reTB-Host-mod.apk" --keystore "$KEYSTORE"
python3 tools/make_images.py --apk "$OUT/TerraBattle-mod.apk" --gdres "$GDRES" \
    --recipe images.json --out "$OUT/gdresources"
echo "done: $OUT/TerraBattle-mod.apk  $OUT/reTB-Host-mod.apk  $OUT/gdresources/"
