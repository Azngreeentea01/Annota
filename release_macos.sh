#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

VERSION="0.2.0"
ARCH="$(uname -m)"
RELEASE_DIR="releases/v$VERSION"
STAGE="$RELEASE_DIR/Annota-v$VERSION-macOS-$ARCH"
DMG="$RELEASE_DIR/Annota-v$VERSION-macOS-$ARCH.dmg"
SHA="$DMG.sha256"

./build_macos.sh

rm -rf "$STAGE" "$DMG" "$SHA"
mkdir -p "$STAGE"
cp -R dist/Annota.app "$STAGE/Annota.app"
cp README.md "$STAGE/README.md"
cp LICENSE "$STAGE/LICENSE"

hdiutil create \
  -volname "Annota v$VERSION" \
  -srcfolder "$STAGE" \
  -ov \
  -format UDZO \
  "$DMG"

if [[ -n "${MACOS_NOTARY_PROFILE:-}" ]]; then
  echo "[Annota] Submitting DMG for notarization"
  xcrun notarytool submit "$DMG" --keychain-profile "$MACOS_NOTARY_PROFILE" --wait
  xcrun stapler staple "$DMG"
fi

shasum -a 256 "$DMG" | awk '{print toupper($1) "  " $2}' > "$SHA"
rm -rf "$STAGE"

echo
echo "macOS release package complete:"
echo "  $DMG"
echo "  $SHA"
echo
echo "Before publishing, open the DMG on a real Mac and complete the macOS acceptance checklist."
