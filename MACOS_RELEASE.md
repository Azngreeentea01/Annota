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


## GitHub-hosted Apple Silicon build

The repository includes `.github/workflows/macos-arm64-build.yml` for a native ARM64 release-candidate build on GitHub's standard `macos-15` Apple Silicon runner.

The workflow:

1. Checks out the repository.
2. Selects Python 3.13.
3. Compiles source and runs the full pytest suite.
4. Builds and signs `Annota.app`, then verifies the bundle identifier `net.softwify.annota`.
5. Compiles the native Swift/Carbon global-hotkey helper and proves that `Option+Q` can be registered on the Apple Silicon runner.
6. Runs the packaged `--self-test` and `--smoke-test` so an app that crashes immediately cannot be published.
7. Creates the DMG plus SHA-256 and publishes them directly to a GitHub prerelease.

It intentionally does not use `actions/upload-artifact` or GitHub Actions artifact storage. The GitHub-hosted build is still a release candidate until the real-Mac acceptance checklist below passes.

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
releases/v0.2.2/Annota-v0.2.2-macOS-arm64.dmg
releases/v0.2.2/Annota-v0.2.2-macOS-arm64.dmg.sha256
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
- **Accessibility**: may be required for automated paste into another app. The native Option+Q Quick Capture registration does not require Accessibility.

Annota v0.2.2 includes a visible macOS setup window with permission status, direct Settings access for changing Quick Capture, links to Privacy & Security, and a Start Annotation button. Quick Capture is registered by a bundled native macOS helper rather than relying on global keyboard monitoring. Restart Annota once after changing privacy permissions if macOS requests it.

## macOS acceptance checklist

Do not publish a macOS build until all of these pass on the actual release machine:

- `.app` launches without a console window.
- Menu-bar/tray icon appears and Quit terminates fully.
- Option+Q opens Annotation Mode through the bundled native macOS hotkey helper.
- Settings is reachable from the setup window and changing Quick Capture applies without restarting Annota.
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

v0.2.2 is the macOS recovery line after v0.2.1 failed physical-Mac use. GitHub-hosted ARM64 QA must pass compilation, tests, packaged self-test, packaged launch smoke test, signing, DMG creation, and checksum generation before an RC is published. The RC remains a prerelease until a physical-Mac acceptance pass confirms launch, permissions, menu-bar controls, Option+Q, annotation/review, and insertion/fallback behavior.
