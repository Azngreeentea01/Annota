# Annota

Annota is a lightweight local-first desktop annotation utility for visual development feedback. On Windows, start from the desktop/File Explorer context menu, the system tray, or `Alt+Q`. On macOS, the target shortcut is `Option+Q`. Select visible UI regions, attach numbered comments, review the marked screenshot and every comment, then insert the image plus structured notes into Codex/ChatGPT for review before you send the chat message yourself.

## Product principles
- Invisible when idle, instant when activated, gone when finished.
- Single lavender visual language; no theme switching.
- Native Windows release first, with native macOS build/release support from the same source.
- No Electron or Chromium embedding.
- No telemetry, account, cloud dependency, continuous recording, or background AI.
- Annota never presses the final chat Send button automatically.
- Annota never bypasses its own Review screen before inserting an annotation payload.

## Ways to start an annotation
- Windows: `Alt+Q`
- System tray/menu-bar tray: `Annotate Now`
- Windows desktop/File Explorer background: right-click -> `Show more options` -> `Annota`
- macOS target: `Option+Q`

The Windows context-menu command launches Annotation Mode immediately. If Annota is already running in the tray, the second launch forwards the annotate request to the existing process instead of creating another tray instance.

Windows 11 note: the current unpackaged EXE uses the standard per-user Win32 shell verb, so Windows 11 shows it under `Show more options`. A future MSIX/sparse-package shell extension can promote Annota into the modern first-level Windows 11 context menu.

The keyboard shortcut can be changed, reset, paused, and checked for common Windows conflicts.

## Current annotation workflow
1. Annota runs in the system tray/menu-bar tray.
2. Start Annotation Mode with the platform shortcut or `Annotate Now`. Windows also supports the right-click `Annota` command.
3. The monitor under the pointer is captured once, dimmed, and outlined in lavender.
4. Drag a region around the UI issue, then move or resize the selection if needed.
5. Enter the comment in **What should change?**.
6. Choose one of the actions directly on the comment card:
   - **+ New Annotation** saves the current comment and immediately returns to selection mode so another region can be marked.
   - **Auto Send** saves the current comment and opens Review. It does **not** insert anything yet.
   - Use the arrow beside Auto Send to select Codex, ChatGPT desktop, ChatGPT web, or manual paste. Selecting a destination changes the main button label, but still does not insert anything yet.
7. Repeat **+ New Annotation** as many times as needed. Markers and comments remain numbered `1, 2, 3...`.
8. When Auto Send or a selected destination is chosen, Annota opens **Review your annotations**.
9. Review shows the complete annotated screenshot on the left and every matching numbered comment on the right.
10. From Review, choose **+ New Annotation** to continue, **Cancel** to return without sending, or the final **Auto Send / Send to ...** button to insert the payload.
11. Only that final Review action creates the PNG/TXT/JSON payload and performs destination routing.
12. Review the destination composer and press the chat application's final Send button yourself.

`Ctrl+Enter` cannot bypass Review; when annotations are ready it opens Review instead of sending directly.

## Smart Send routing
The default primary action is **Auto Send**. On Windows it uses this destination priority after Review confirmation:
1. Codex view/window
2. ChatGPT desktop
3. ChatGPT web in a supported browser
4. Clipboard/manual-paste fallback

If Codex and ChatGPT are both available, Codex wins automatically.

The arrow beside Auto Send provides one-send choices:
- Auto Send (Recommended)
- Send to Codex
- Send to ChatGPT desktop
- Send to ChatGPT web
- Copy for manual paste

Choosing a specific destination changes the primary button label, for example from `Auto Send` to `Send to Codex`. The selection carries through additional annotations and into Review. Closing the complete annotation session resets the next session back to Auto Send.

If no requested target can be found or focused, Annota falls back to the manual-paste flow and keeps the local PNG/TXT/JSON payload. macOS target routing must be acceptance-tested on the release Mac before publication; clipboard/manual-paste fallback remains the safe path when a target cannot be focused.

## Review requirement
Review is a mandatory confirmation gate before payload insertion. It contains:
- complete annotated screenshot preview
- every numbered marker
- every matching user comment
- `+ New Annotation`
- `Cancel`
- destination-aware `Auto Send` / `Send to ...` control

No note-card or toolbar action inserts content directly into Codex/ChatGPT.

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

Package the current release when its versioned release script is ready:
```bat
release_windows.bat
```

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

For ARM64 release-candidate builds, `.github/workflows/macos-arm64-build.yml` uses GitHub's standard `macos-15` Apple Silicon runner. It publishes the DMG and SHA-256 directly to a GitHub prerelease and intentionally does not use Actions artifact storage. A real-Mac acceptance pass is still required before production release.

## Privacy
Screen capture happens only after explicit annotation activation. No capture is uploaded by Annota itself. Temporary payloads use the operating system temporary directory under an `Annota` folder.

## Version status
- `v0.2.0`: packaged Windows baseline and initial macOS build-kit baseline.
- `v0.2.1` development: new comment-card action flow, **+ New Annotation**, mandatory Review before insertion, destination-aware **Auto Send**, and route-label persistence/reset behavior.
- macOS `v0.2.1` release remains gated on native Mac build and acceptance testing.

## License
MIT. See `LICENSE`.
