#!/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")"

VERSION="0.2.5"
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
"$PYTHON" -m pip install -r requirements-dev.txt

STAGE="generate icon assets"
"$PYTHON" tools/make_icons.py

STAGE="convert Apple iconset to ICNS"
if ! command -v iconutil >/dev/null 2>&1; then
  echo "iconutil was not found. Run this build on macOS."
  exit 1
fi
rm -f assets/annota.icns
iconutil -c icns assets/Annota.iconset -o assets/annota.icns

STAGE="lint and verify Python formatting"
"$PYTHON" -m ruff check main.py tests tools
"$PYTHON" -m ruff format --check main.py tests tools

STAGE="compile Python source"
"$PYTHON" -m compileall -q main.py tests tools

STAGE="run pytest suite"
QT_QPA_PLATFORM=offscreen "$PYTHON" -m pytest -q

STAGE="compile native macOS global-hotkey helper"
rm -rf .macos-native
mkdir -p .macos-native
swiftc tools/annota_hotkey.swift -o .macos-native/annota_hotkey
chmod +x .macos-native/annota_hotkey
test -x .macos-native/annota_hotkey

STAGE="verify native Option+Q registration"
rm -f .macos-native/hotkey.out .macos-native/hotkey.err
.macos-native/annota_hotkey "Option+Q" >.macos-native/hotkey.out 2>.macos-native/hotkey.err &
HOTKEY_PID=$!
HOTKEY_READY=0
for _ in {1..30}; do
  if grep -q '^READY Option+Q$' .macos-native/hotkey.out 2>/dev/null; then
    HOTKEY_READY=1
    break
  fi
  if ! kill -0 "$HOTKEY_PID" 2>/dev/null; then
    cat .macos-native/hotkey.err || true
    exit 1
  fi
  sleep 0.1
done
if [[ "$HOTKEY_READY" != "1" ]]; then
  cat .macos-native/hotkey.out || true
  cat .macos-native/hotkey.err || true
  kill "$HOTKEY_PID" 2>/dev/null || true
  wait "$HOTKEY_PID" 2>/dev/null || true
  echo "Native Option+Q helper did not report READY."
  exit 1
fi
kill "$HOTKEY_PID" 2>/dev/null || true
wait "$HOTKEY_PID" 2>/dev/null || true

STAGE="clean previous macOS build"
rm -rf build dist/Annota.app

STAGE="build Annota.app with PyInstaller"
"$PYTHON" -m PyInstaller \
  --noconfirm \
  --clean \
  --specpath build \
  --windowed \
  --onedir \
  --name Annota \
  --osx-bundle-identifier net.softwify.annota \
  --icon "$PWD/assets/annota.icns" \
  --add-data "$PWD/assets:assets" \
  --add-binary "$PWD/.macos-native/annota_hotkey:." \
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
