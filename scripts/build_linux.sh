#!/bin/bash
# Build VoxWave pour Linux (AppImage)
# Usage: ./scripts/build_linux.sh [clean|build|all]
#
# Prerequis:
#   pip install pyinstaller
#   sudo apt install libportaudio2
#   # Pour l'AppImage, installer appimagetool:
#   wget https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
#   chmod +x appimagetool-x86_64.AppImage
#   sudo mv appimagetool-x86_64.AppImage /usr/local/bin/appimagetool

set -e

echo "========================================"
echo " VoxWave Build Script (Linux)"
echo "========================================"

cd "$(dirname "$0")/.."

CMD="${1:-all}"
python3 build.py "$CMD" --platform linux

echo ""
echo "BUILD SUCCESS"
