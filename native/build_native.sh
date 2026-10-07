#!/bin/sh
# Builds the two small native helpers into ../tools:
#   libetc2.so - ETC2_RGBA8 texture encoder (wraps etcpak by Bartosz Taudul, BSD-3)
#   liblz4.so  - LZ4 / LZ4-HC for UnityFS blocks (BSD-2)
# Needs: git, g++, make
set -e
cd "$(dirname "$0")"
OUT=../tools
[ -d etcpak ] || git clone --depth 1 --recursive https://github.com/K0lb3/etcpak.git etcpak
E=etcpak/src/etcpak
g++ -O2 -shared -fPIC -std=c++17 -I"$E" etc2wrap.cpp "$E/ProcessRGB.cpp" "$E/Tables.cpp" "$E/Dither.cpp" -o "$OUT/libetc2.so"
[ -d lz4 ] || git clone --depth 1 https://github.com/lz4/lz4.git lz4
make -C lz4/lib liblz4.so >/dev/null
cp -L lz4/lib/liblz4.so "$OUT/liblz4.so"
echo "built $OUT/libetc2.so $OUT/liblz4.so"
