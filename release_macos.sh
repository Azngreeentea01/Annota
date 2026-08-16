#!/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")"

VERSION="0.2.1"
ARCH="$(uname -m)"
RELEASE_DIR="releases/v$VERSION"
STAGE="$RELEASE_DIR/Annota-v$VERSION-macOS-$ARCH"
DMG="$RELEASE_DIR/Annota-v$VERSION-macOS-$ARCH.dmg"
SHA="$DMG.sha256"
CURRENT_STAGE="startup"

on_error() {
  code=$?
  trap - ERR
  echo "::error title=Annota macOS packaging failed::Stage: ${CURRENT_STAGE} (exit ${code})"
  exit "$code"
}
trap on_error ERR

if [[ "${ANNOTA_SKIP_BUILD:-0}" != "1" ]]; then
  CURRENT_STAGE="build native Annota.app"
  ./build_macos.sh
fi

CURRENT_STAGE="verify native app before packaging"
test -d dist/Annota.app

CURRENT_STAGE="stage DMG contents"
rm -rf "$STAGE" "$DMG" "$SHA"
mkdir -p "$STAGE"
cp -R dist/Annota.app "$STAGE/Annota.app"
cp README.md "$STAGE/README.md"
cp LICENSE "$STAGE/LICENSE"

CURRENT_STAGE="create compressed DMG"
hdiutil create \
  -volname "Annota v$VERSION" \
  -srcfolder "$STAGE" \
  -ov \
  -format UDZO \
  "$DMG"

if [[ -n "${MACOS_NOTARY_PROFILE:-}" ]]; then
  CURRENT_STAGE="notarize DMG"
  echo "[Annota] Submitting DMG for notarization"
  xcrun notarytool submit "$DMG" --keychain-profile "$MACOS_NOTARY_PROFILE" --wait
  xcrun stapler staple "$DMG"
fi

CURRENT_STAGE="generate SHA-256"
shasum -a 256 "$DMG" | awk '{print toupper($1) "  " $2}' > "$SHA"

CURRENT_STAGE="clean staging directory"
rm -rf "$STAGE"

CURRENT_STAGE="complete"
trap - ERR
echo
echo "macOS release package complete:"
echo "  $DMG"
echo "  $SHA"
echo
echo "This GitHub-hosted build is a release candidate until it passes real-Mac acceptance testing."
