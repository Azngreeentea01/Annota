# Annota

Annota is a lightweight local-first desktop annotation utility for visual development feedback. On Windows, start from the desktop/File Explorer context menu, the system tray, or `Alt+Q`. On macOS, the target shortcut is `Option+Q`. Select any visible UI region, attach numbered notes, review the marked screenshot, and insert the image plus structured notes for review before sending.

## Product principles
- Invisible when idle, instant when activated, gone when finished.
- Single lavender visual language; no theme switching.
- Native Windows release first, with native macOS build/release support from the same source.
- No Electron or Chromium embedding.
- No telemetry, account, cloud dependency, continuous recording, or background AI.
- Annota never presses the final chat Send button automatically.

## Ways to start an annotation
- Windows: `Alt+Q`
- System tray/menu-bar tray: `Annotate Now`
- Windows desktop/File Explorer background: right-click -> `Show more options` -> `Annota`
- macOS target: `Option+Q`

The Windows context-menu command launches Annotation Mode immediately. If Annota is already running in the tray, the second launch forwards the annotate request to the existing process instead of creating another tray instance.

Windows 11 note: the current unpackaged EXE uses the standard per-user Win32 shell verb, so Windows 11 shows it under `Show more options`. A future MSIX/sparse-package shell extension can promote Annota into the modern first-level Windows 11 context menu.

The keyboard shortcut can be changed, reset, paused, and checked for common Windows conflicts.

## Current workflow
1. Annota runs in the system tray/menu-bar tray.
2. Start Annotation Mode with the platform shortcut or `Annotate Now`. Windows also supports the right-click `Annota` command.
3. The monitor under the pointer is captured once, dimmed, and outlined in lavender.
4. Drag a region around the UI issue.
5. Move the selection by dragging inside it or resize from any corner.
6. Add a note and save it.
7. Add more numbered annotations as needed.
8. Open Review to see the annotated screenshot beside the numbered note list.
9. Click `Send` for automatic destination selection where supported, or use the small arrow beside Send to choose a destination for this send only.
10. Annota creates PNG, TXT, and JSON payload files and inserts/copies the image plus notes according to the available route.
11. Review the composer and send manually.

## Smart Send routing
On Windows, a normal `Send` click uses this priority:
1. Codex view/window
2. ChatGPT desktop
3. ChatGPT web in a supported browser
4. Clipboard/manual-paste fallback

If Codex and ChatGPT are both available, Codex wins automatically.

The Send arrow provides one-send overrides:
- Send to Codex
- Send to ChatGPT desktop
- Send to ChatGPT web
- Copy for manual paste

If no requested target can be found or focused, Annota falls back to the manual-paste flow and keeps the local PNG/TXT/JSON payload. macOS target routing must be acceptance-tested on the release Mac before publication; clipboard/manual-paste fallback remains the safe path when a target cannot be focused.

## Payload metadata
The JSON payload includes:
- source application executable/name where available
- source window title where available
- logical display resolution
- monitor geometry
- device pixel ratio / DPI scale
- UTC capture timestamp
- UTC payload timestamp
- context padding percentage
- numbered notes
- local selection coordinates
- global screen coordinates
- local paths to the PNG and TXT payload

## Settings
- Change shortcut
- Reset shortcut
- Detect common Windows shortcut conflicts
- Start with Windows
- Pause global shortcut
- Clear clipboard after successful insertion
- Context padding: 0-50%
- About/version/privacy information

## Visual language
Primary lavender: `#B9A7FF`
Active purple: `#8E68F4`
Soft lavender: `#EEE9FF`

Lavender means annotation mode is active. Selection borders, markers, review actions, icons, and status surfaces use the same family.

## Install from source on Windows
```powershell
cd C:\Projects\Annota
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python main.py
```

## Build Windows release locally
Fast one-folder build:
```bat
build.bat
```

Output:
`dist\Annota\Annota.exe`

Package the Windows x64 release:
```bat
release_windows.bat
```

Release output:
`releases\v0.2.0\Annota-v0.2.0-Windows-x64.zip`

Portable one-file build:
```bat
build_onefile.bat
```

Windows build scripts create a local virtual environment when needed, install requirements locally, generate icons, run source compilation and pytest, package assets, and generate SHA-256 verification files. No GitHub Actions, runners, artifacts, Action storage, or GitAI are used.

## Build macOS release
macOS must be built natively on a Mac. The project includes:
- `build_macos.sh` -> builds `dist/Annota.app`
- `release_macos.sh` -> creates an architecture-specific `.dmg` and SHA-256 file
- `release_macos_kit.bat` -> creates a portable macOS source/build kit from Windows
- `MACOS_RELEASE.md` -> signing, notarization, permissions, and acceptance instructions
- `assets/Annota.iconset` -> native Apple icon resources generated from the same Annota artwork

On macOS:
```bash
chmod +x build_macos.sh release_macos.sh
./release_macos.sh
```

A production macOS release must be built and acceptance-tested on the actual Mac. Screen Recording and Accessibility permissions may be required for capture, global shortcuts, and paste automation.

## Privacy
Screen capture happens only after explicit annotation activation. No capture is uploaded by Annota itself. Temporary payloads use the operating system temporary directory under an `Annota` folder.

## Release status
- Windows x64 v0.2.0: packaged locally and validated with the permanent automated suite.
- macOS v0.2.0: build/release tooling and build kit are ready; native `.app`/`.dmg` publication remains gated on a real-macOS build and acceptance test.

## License
MIT. See `LICENSE`.
