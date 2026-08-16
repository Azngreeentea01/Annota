# Annota macOS Release Guide

Annota is designed to remain local-first on macOS. The macOS release is built natively on a Mac from the same readable Python source used by Windows.

## Build requirements

- A supported macOS machine.
- `python3` available in Terminal.
- Xcode Command Line Tools so `iconutil`, `codesign`, `hdiutil`, `xcrun`, and `shasum` are available.
- Internet access during the first build so Python packages in `requirements.txt` can be installed.

## Build the app

```bash
chmod +x build_macos.sh release_macos.sh
./build_macos.sh
```

Output:

```text
dist/Annota.app
```

The build script:

1. Creates `.venv-macos` when needed.
2. Installs only `requirements.txt` dependencies.
3. Generates the shared Annota artwork plus a native Apple iconset.
4. Converts the iconset to `assets/annota.icns` with `iconutil`.
5. Runs Python compilation and the full pytest suite.
6. Builds a native `.app` with PyInstaller.
7. Applies an ad-hoc signature for local testing unless a Developer ID identity is supplied.

## Developer ID signing

For a distributable signed build, export your Developer ID Application identity before running the build:

```bash
export MACOS_CODESIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)"
./build_macos.sh
```

## Create the DMG release

```bash
./release_macos.sh
```

Output names are architecture-specific, for example:

```text
releases/v0.2.0/Annota-v0.2.0-macOS-arm64.dmg
releases/v0.2.0/Annota-v0.2.0-macOS-arm64.dmg.sha256
```

On an Intel Mac the architecture suffix will be `x86_64`.

## Optional notarization

If a `notarytool` keychain profile is configured, export its profile name before packaging:

```bash
export MACOS_NOTARY_PROFILE="annota-notary"
./release_macos.sh
```

The release script submits the DMG, waits for notarization, and staples the result.

## macOS permissions

Annota may require macOS privacy permissions for its desktop workflow:

- **Screen Recording**: required for desktop capture.
- **Accessibility**: may be required for the global Option+Q shortcut and automated paste into the current app.

Open System Settings -> Privacy & Security if macOS prompts for either permission. Restart Annota after granting a permission if macOS requests it.

## macOS acceptance checklist

Do not publish a macOS build until all of these pass on the actual release machine:

- `.app` launches without a console window.
- Menu-bar/tray icon appears and Quit terminates fully.
- Option+Q opens Annotation Mode.
- Capture works after Screen Recording permission is granted.
- Selection, move, resize, note entry, multiple annotations, and Review work.
- Retina rendering is sharp and marker/text sizing is correct.
- Clipboard fallback preserves PNG + notes + JSON locally.
- Paste automation works after Accessibility permission is granted.
- Pause Shortcut, custom shortcut, context padding, and clipboard settings persist.
- App relaunch works after signing/notarization.
- DMG opens normally and the app launches after being copied from the DMG.
- Apple silicon build is tested on Apple silicon.
- Intel build is tested on Intel hardware if an Intel release is published.

## Current release status

The macOS build and packaging path is present in the project, but a production macOS binary must be generated and acceptance-tested on macOS. Windows cannot produce or validate the final native `.app`/`.dmg` release.
