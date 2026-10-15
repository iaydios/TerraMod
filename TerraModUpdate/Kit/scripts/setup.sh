#!/bin/bash
# One-time setup inside Linux (WSL Ubuntu). Safe to re-run.
set -e
SUDO=""; [ "$(id -u)" != 0 ] && SUDO="sudo"
$SUDO apt-get update -qq
$SUDO apt-get install -y -qq python3 python3-pip python3-venv gcc default-jre-headless apksigner zipalign llvm unzip zip
python3 -m pip install -q --break-system-packages UnityPy capstone unicorn pillow scipy numpy 2>/dev/null \
  || python3 -m pip install -q UnityPy capstone unicorn pillow scipy numpy
echo "setup ok"
