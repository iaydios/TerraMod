#!/bin/bash
# run_combo.sh <combo.txt> <OUT dir> : builds one APK from every Update folder named in combo.txt
cd "$(dirname "$0")"
LIST=$(tr -d '\r' < "$1" | grep -v '^#' | grep -v '^[[:space:]]*$' | tr '\n' ' ')
[ -n "$LIST" ] || { echo "combo.txt is empty"; exit 1; }
echo "combo: $LIST"
bash run.sh "$2" $LIST
