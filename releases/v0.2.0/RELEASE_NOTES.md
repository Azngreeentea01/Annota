# Annota v0.2.0

## Windows x64 release

Annota is a lightweight, local-first desktop annotation utility for sending precise visual feedback into Codex and ChatGPT workflows.

### Highlights
- Tray-first Windows desktop app with Alt+Q Quick Annotate.
- Capture the active monitor only when annotation mode starts.
- Drag, move, and resize highlighted regions.
- Add multiple numbered annotations with notes.
- Review the annotated screenshot and notes before insertion.
- Smart Send routing priority: Codex, ChatGPT desktop, ChatGPT web, then clipboard/manual-paste fallback.
- One-send route override menu.
- Windows desktop/File Explorer background context-menu integration.
- Single-instance forwarding for `Annota.exe --annotate`.
- Local-only temporary payloads.
- High-clarity lavender UI and high-quality multi-size Windows icon.
- No telemetry, account, cloud storage, continuous recording, or background AI.

### Release validation
- Permanent automated test suite: 23/23 PASS after cross-platform release support was added.
- Python source compilation: PASS.
- Clean Windows x64 one-folder PyInstaller build: PASS.
- Source-native package smoke test: PASS.
- SHA-256 sidecar generated for the Windows release package.

### Windows package
Use `Annota-v0.2.0-Windows-x64.zip`. Extract the folder and run `Annota.exe`.

### Known Windows validation limit
The latest source-native package has passed automated and package smoke testing. A fresh interactive visual pass on the exact final package remains dependent on the Windows UI automation service being available. Previous Annota Windows acceptance testing covered the tray, annotation flow, Review, route menu, clipboard fallback, shell context menu, and single-instance forwarding at 100% scaling.

## macOS v0.2.0 preparation

The project now includes native macOS release support from the same source:
- `build_macos.sh` for `Annota.app`
- `release_macos.sh` for architecture-specific `.dmg` packaging
- generated Apple `Annota.iconset`
- optional Developer ID signing
- optional Apple notarization/stapling
- `MACOS_RELEASE.md` acceptance and permissions guide
- `Annota-v0.2.0-macOS-Build-Kit.zip` for transfer to a Mac

The macOS build kit is **not** a production macOS binary. The final `.app`/`.dmg` must be generated and acceptance-tested on a real Mac before publication.
