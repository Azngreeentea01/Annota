# Annota QA Plan

## Release gate
Annota is not production-ready until all automated checks pass, the Windows EXE builds locally, and the full annotation workflow is manually verified on the Windows VM. No GitHub Actions, runners, artifacts, Action storage, or GitAI are used.

## Core launch and background behavior
- App starts without a visible main window.
- Tray icon appears and remains responsive.
- Idle CPU remains effectively zero while no shortcut is pressed.
- Shortcut listener remains active after repeated annotation sessions.
- Quit fully terminates the tray process and shortcut listener.

## Global shortcut
- Windows default: Alt+Q.
- macOS target: Option+Q.
- Custom shortcut saves and applies without restart.
- Reset restores the platform default.
- Pause Shortcut disables global activation while tray Annotate Now remains available.
- Invalid shortcut input is rejected.
- Windows shortcut conflict detection warns before saving a conflicting shortcut.

## Windows context-menu launch
- Per-user shell verb is registered for the Windows desktop background and File Explorer folder background.
- Windows 11 flow: right-click background -> Show more options -> Annota.
- Registered command launches `Annota.exe --annotate`.
- If Annota is already running, the new invocation forwards Annotation Mode to the existing tray process instead of creating a second tray instance.
- Current unpackaged EXE uses the classic Win32 shell verb. A first-level modern Windows 11 menu item requires the later IExplorerCommand + app identity/MSIX/sparse-package milestone.

## Annotation activation
- Screen capture occurs only when annotation mode starts.
- Active monitor dims immediately.
- Lavender border appears around the active monitor.
- Crosshair cursor appears.
- Annotation Mode pill is visible and readable.
- Escape exits safely.

## Region selection
- Dragging creates a lavender selection rectangle.
- Very small accidental drags are ignored.
- Selected area remains bright while outside area is dimmed.
- Selection can be moved by dragging inside it.
- All four corner handles resize the selection.
- Selection cannot be moved outside the active monitor.
- Minimum selection size remains usable.
- Note card follows moved/resized selection.
- Marker number matches the note number.

## Multiple annotations
- Add another creates the next numbered annotation.
- Every note remains tied to its correct marker.
- Review lists notes in numeric order.
- Final image contains all highlighted regions and matching markers.
- Context padding includes nearby UI without losing selected content.

## Review screen
- Review opens as a centered lavender/light panel.
- Left side shows the annotated screenshot preview.
- Right side lists numbered notes.
- Add another returns to annotation mode.
- Cancel closes review without sending.
- Send creates the payload and begins smart target selection.
- Send target dropdown is available beside the main Send button.

## Payload
Payload must include:
- annotated PNG
- notes text
- JSON metadata
- application executable name
- source window title
- display resolution
- display geometry
- device pixel ratio / DPI scale
- UTC capture timestamp
- UTC payload timestamp
- local annotation rectangles
- global/screen annotation rectangles
- context padding percentage

Temporary payloads are stored only in %TEMP%\Annota.

## Smart Send and fallback
Normal Send target priority:
1. Codex view/window
2. ChatGPT desktop
3. ChatGPT web in a supported browser
4. Clipboard/manual-paste fallback

One-send override menu:
- Send to Codex
- Send to ChatGPT desktop
- Send to ChatGPT web
- Copy for manual paste

Acceptance requirements:
- If Codex and ChatGPT are both open, Codex wins automatically.
- A route chosen from the annotation toolbar survives into Review and is applied when Review Send is clicked.
- Review Cancel, Add another, or close clears a pending one-send route.
- Screenshot is pasted first.
- Structured notes are pasted second.
- Annota never presses the final chat Send button.
- Sending state uses an Annota lavender status toast.
- Success state confirms insertion and reminds user to review.
- If no requested chat target exists, a clipboard fallback is created.
- PNG, TXT, and JSON remain available in %TEMP%\Annota.
- No annotation is silently lost.

## Settings
- Shortcut can be changed and reset.
- Start with Windows writes/removes the current-user startup entry.
- Pause shortcut persists.
- Clear clipboard after insertion persists.
- Context padding 0-50% persists.
- About section shows version, brand, license, and privacy statement.

## Privacy/performance
- No continuous screenshot capture.
- No telemetry.
- No network requests from Annota except the local-only single-instance UDP message on 127.0.0.1.
- No cloud storage.
- No background AI.
- No Chromium/Electron runtime.
- Idle CPU should be effectively zero.
- Memory usage should remain appropriate for a small PySide6 tray utility.

## Windows matrix
Manually verify:
- Windows 10
- Windows 11
- 100%, 125%, 150%, 200% DPI
- 1080p, 1440p, 4K
- multiple monitors including monitors with different scaling
- negative virtual-screen coordinates (monitor left of primary)

## Failure/reliability matrix
- Codex closed
- ChatGPT closed
- current chat cannot be focused
- pynput unavailable
- invalid selection
- cancel during selection
- cancel during note entry
- cancel during review
- repeated Alt+Q while overlay already open
- shortcut paused
- clipboard changes before delayed cleanup

## Packaging
- build.bat creates one-folder Windows build.
- build_onefile.bat creates optional portable one-file build.
- Both scripts create .venv when missing.
- Both install requirements locally.
- Both generate icons locally.
- Both run compileall and pytest before packaging.
- All assets are bundled.
- EXE is built with no console window.
- SHA256 sidecar is produced after successful build.

## Current automated checks
- Python compileall / VM Command MCP syntax compilation.
- Shortcut normalization tests.
- Geometry helper tests.
- Payload model/timestamp tests.
- Smart target classification tests.
- Codex-first routing priority test.
- Explicit web/clipboard routing tests.
- Windows shell command quoting/`--annotate` test.

## Windows 11 acceptance results — 2026-08-16
Environment: Windows 11 VM, 1470x923 logical desktop, 100% scaling.

- Packaged tray-first startup: PASS.
- High-clarity annotation UI: PASS.
- Note -> Save -> toolbar -> Review flow: PASS.
- Send dropdown visible in annotation toolbar: PASS.
- Send dropdown visible in Review: PASS.
- Dropdown choices Codex / ChatGPT desktop / ChatGPT web / manual paste: PASS.
- Toolbar route persistence through Review: PASS. Verified using Copy for manual paste -> Review -> normal Send, which produced the fallback notification/toast.
- Clipboard/manual-paste fallback: PASS.
- Windows 11 modern right-click menu exposes Show more options: PASS.
- Classic background menu shows Annota as the first item: PASS.
- Shell command registered to the current packaged EXE with `--annotate`: PASS.
- Right-click Show more options -> Annota opened Annotation Mode: PASS.
- Existing tray process received the right-click request in the same PID (2772): PASS.
- No duplicate Annota tray icon after forwarded launch: PASS.
- Real Codex/ChatGPT composer insertion: NOT TESTED in this VM session because no usable Codex/ChatGPT target window was available.
- 125%/150%/200% DPI, 1440p/4K, mixed-DPI multi-monitor, and negative-coordinate monitor matrix: NOT TESTED in this VM session.

## Manual acceptance sequence
1. Start Annota and verify tray-only idle state.
2. Test Windows right-click -> Show more options -> Annota and confirm the same tray process opens Annotation Mode.
3. Press Alt+Q over a target application.
4. Select a region, resize it, move it, and save a note.
5. Add two more annotations.
6. Open Review and compare screenshot markers to notes.
7. Test normal Send priority with Codex + ChatGPT targets open together.
8. Test each Send dropdown override.
9. Close Codex/ChatGPT and repeat to verify clipboard fallback.
10. Test Escape/cancel at every stage.
11. Test shortcut change/reset/conflict/pause.
12. Build one-folder EXE locally and repeat the workflow from the packaged EXE.
