#!/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")"

VERSION="0.2.2"
VENV=".venv-macos"
PYTHON="$VENV/bin/python"
STAGE="startup"

on_error() {
  code=$?
  trap - ERR
  echo "::error title=Annota macOS build failed::Stage: ${STAGE} (exit ${code})"
  exit "$code"
}
trap on_error ERR

echo "[Annota] macOS app build v$VERSION"

STAGE="create Python virtual environment"
if [[ ! -x "$PYTHON" ]]; then
  python3 -m venv "$VENV"
fi

STAGE="upgrade pip"
"$PYTHON" -m pip install --upgrade pip

STAGE="install Python dependencies"
"$PYTHON" -m pip install -r requirements.txt

STAGE="generate icon assets"
"$PYTHON" tools/make_icons.py

STAGE="convert Apple iconset to ICNS"
if ! command -v iconutil >/dev/null 2>&1; then
  echo "iconutil was not found. Run this build on macOS."
  exit 1
fi
rm -f assets/annota.icns
iconutil -c icns assets/Annota.iconset -o assets/annota.icns

STAGE="compile Python source"
"$PYTHON" -m compileall -q main.py tests tools

STAGE="run pytest suite"
QT_QPA_PLATFORM=offscreen "$PYTHON" -m pytest -q

STAGE="clean previous macOS build"
rm -rf build dist/Annota.app

STAGE="build Annota.app with PyInstaller"
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

STAGE="verify Annota.app exists"
if [[ ! -d "dist/Annota.app" ]]; then
  echo "Expected dist/Annota.app was not created."
  exit 1
fi

if [[ -n "${MACOS_CODESIGN_IDENTITY:-}" ]]; then
  STAGE="Developer ID code signing"
  echo "[Annota] Code signing with configured Developer ID identity"
  codesign --force --deep --options runtime --timestamp \
    --sign "$MACOS_CODESIGN_IDENTITY" \
    dist/Annota.app
else
  STAGE="ad-hoc code signing"
  echo "[Annota] No MACOS_CODESIGN_IDENTITY set; applying ad-hoc signature for build verification"
  codesign --force --deep --sign - dist/Annota.app
fi

STAGE="verify app code signature"
codesign --verify --deep --strict --verbose=2 dist/Annota.app

STAGE="complete"
trap - ERR
echo
echo "Build complete: dist/Annota.app"
echo "Architecture: $(uname -m)"
