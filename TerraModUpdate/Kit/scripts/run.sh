#!/bin/bash
# run.sh <OUT dir> <UpdateFolder>...   : installs the Linux packages once (if missing), then builds.
cd "$(dirname "$0")"
if ! command -v llvm-mc >/dev/null 2>&1 && ! ls /usr/bin/llvm-mc* >/dev/null 2>&1 || ! command -v apksigner >/dev/null 2>&1; then bash setup.sh; fi
bash build.sh "$@"
