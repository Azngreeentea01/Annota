#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

VERSION="0.2.0"
VENV=".venv-macos"
PYTHON="$VENV/bin/python"

echo "[Annota] macOS app build v$VERSION"

if [[ ! -x "$PYTHON" ]]; then
  python3 -m venv "$VENV"
fi

"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements.txt
"$PYTHON" tools/make_icons.py

if ! command -v iconutil >/dev/null 2>&1; then
  echo "iconutil was not found. Run this build on macOS."
  exit 1
fi
iconutil -c icns assets/Annota.iconset -o assets/annota.icns

"$PYTHON" -m compileall -q main.py tests tools
"$PYTHON" -m pytest -q

rm -rf build dist/Annota.app

"$PYTHON" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --onedir \
  --name Annota \
  --osx-bundle-identifier net.softwify.annota \
  --icon assets/annota.icns \
  --add-data "assets:assets" \
  main.py

if [[ ! -d "dist/Annota.app" ]]; then
  echo "Expected dist/Annota.app was not created."
  exit 1
fi

if [[ -n "${MACOS_CODESIGN_IDENTITY:-}" ]]; then
  echo "[Annota] Code signing with configured Developer ID identity"
  codesign --force --deep --options runtime --timestamp \
    --sign "$MACOS_CODESIGN_IDENTITY" \
    dist/Annota.app
  codesign --verify --deep --strict --verbose=2 dist/Annota.app
else
  echo "[Annota] No MACOS_CODESIGN_IDENTITY set; applying ad-hoc signature for local testing"
  codesign --force --deep --sign - dist/Annota.app
fi

echo
echo "Build complete: dist/Annota.app"
echo "Architecture: $(uname -m)"
