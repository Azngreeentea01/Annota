# Annota QA Plan

## Release gate
Annota is not production-ready until all automated checks pass and the platform-specific acceptance gates pass. Windows builds remain local. macOS ARM64 release-candidate builds may use the GitHub-hosted macOS runner approved for this project, but the workflow must not use GitHub Actions artifact storage or GitAI.

## Core launch and background behavior
- App starts without a visible main window.
- Tray icon appears and remains responsive.
- Idle CPU remains effectively zero while no shortcut is pressed.
- Shortcut listener remains active after repeated annotation sessions.
- Quit fully terminates the tray process and shortcut listener.

## Global shortcut
- Windows default: Alt+Q.
- macOS default: Option+Q through the native macOS hotkey helper.
- Custom Quick Capture shortcut saves and applies without restart.
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
- Comment card follows moved/resized selection.
- Marker number matches the comment number.

## Comment card flow
The comment card must expose:
- Cancel
- + New Annotation
- Auto Send
- destination dropdown

Acceptance requirements:
- `+ New Annotation` saves the current comment and immediately returns to selection mode.
- Enter behaves like New Annotation; Shift+Enter adds a new line.
- Auto Send saves the current comment and opens Review. It must not insert a payload directly.
- Selecting a destination changes the primary button label without sending.
- Supported labels include Auto Send, Send to Codex, Send to ChatGPT, Send to ChatGPT Web, and Copy for Manual Paste.
- A selected route persists while the current annotation session continues.
- Closing the complete annotation session resets the next session to Auto Send.

## Multiple annotations
- New Annotation creates the next numbered annotation.
- Every comment remains tied to its correct marker.
- Review lists comments in numeric order.
- Final image contains all highlighted regions and matching markers.
- Context padding includes nearby UI without losing selected content.
- The user can continue directly from Review using + New Annotation.

## Review screen
Review is a mandatory confirmation gate before payload insertion.

Acceptance requirements:
- Review opens as a centered lavender/light panel.
- Left side shows the complete annotated screenshot preview.
- Right side lists every numbered user comment.
- + New Annotation returns directly to annotation selection mode.
- Cancel returns without sending.
- Final Auto Send / Send to ... creates the payload and begins destination routing.
- Destination dropdown remains available beside the final send button.
- A route chosen before Review carries into Review.
- Review can reset a manual route back to Auto Send.
- Ctrl+Enter cannot bypass Review.

## Payload
Payload must include:
- annotated PNG
- comments/notes text
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

Temporary payloads are stored only in %TEMP%\Annota on Windows or the operating-system temporary directory on other platforms.

## Smart Send and fallback
Auto Send target priority:
1. Codex view/window
2. ChatGPT desktop
3. ChatGPT web in a supported browser
4. Clipboard/manual-paste fallback

One-send dropdown choices:
- Auto Send (Recommended)
- Send to Codex
- Send to ChatGPT desktop
- Send to ChatGPT web
- Copy for manual paste

Acceptance requirements:
- If Codex and ChatGPT are both open, Codex wins automatically.
- Choosing a manual route changes the primary button label but does not send immediately.
- The selected route survives additional annotations and Review.
- Screenshot is pasted first.
- Structured comments are pasted second.
- Annota never presses the final chat Send button.
- Sending state uses an Annota lavender status toast.
- Windows success state confirms insertion and reminds user to review.
- macOS success state says paste was requested, not guaranteed, because the destination app does not provide reliable paste acceptance confirmation.
- macOS automatic insertion uses native Quartz Command+V events and rechecks Accessibility/Post Event readiness before each automatic send.
- If macOS image or notes paste cannot be issued, the failure reason is surfaced and clipboard/manual-paste recovery remains available.
- If no requested chat target exists, a clipboard fallback is created.
- PNG, TXT, and JSON remain available locally.
- No annotation is silently lost.

## Settings
- Shortcut can be changed and reset.
- Start with Windows writes/removes the current-user startup entry.
- Pause shortcut persists.
- Windows Clear clipboard after insertion persists.
- macOS intentionally keeps notes on the clipboard after automatic paste attempts as a recovery path.
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
- cancel during comment entry
- cancel during Review
- repeated Alt+Q while overlay already open
- shortcut paused
- clipboard changes before delayed cleanup
- manual destination selected, then entire annotation session cancelled


## macOS GitHub-hosted build gate
- Workflow uses the standard GitHub-hosted `macos-15` ARM64 runner.
- Python 3.13 is explicitly selected.
- Full pytest suite runs before packaging.
- `Annota.app` is built natively with PyInstaller on macOS.
- App code signature is verified.
- Bundle identifier is verified as `net.softwify.annota`.
- Architecture must report `arm64`.
- DMG and SHA-256 are generated.
- DMG and SHA-256 are published directly to a GitHub prerelease.
- `actions/upload-artifact` and `actions/download-artifact` are prohibited.
- GitHub-hosted build must compile the native hotkey helper and successfully register Option+Q before packaging. It remains a release candidate until real-Mac Screen Recording, Option+Q, Settings/change-shortcut, menu-bar, Retina/multi-display, Accessibility-assisted paste, and real target-insertion acceptance tests pass.

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
- Comment-card New Annotation behavior.
- Comment-card Auto Send -> Review path behavior.
- Manual route label behavior without immediate send.
- Route persistence into Review.
- Review final send commits the route.
- Review reset to Auto Send.
- Review footer New Annotation naming contract.
- v0.2.2 mandatory Review/session-reset source contract.
- macOS app classification and source-browser routing tests.
- macOS startup/permission/tray lifetime source contracts.
- Direct macOS Settings/Quick Capture controls and native hotkey helper source/build contracts.
- macOS native Quartz paste, denied-permission behavior, clipboard safety fallback, and send-status regression tests.
- Packaged macOS runtime `--self-test` and timed `--smoke-test` are required in GitHub QA.

## Windows 11 acceptance results - v0.2.0 baseline - 2026-08-16
Environment: Windows 11 VM, 1470x923 logical desktop, 100% scaling.

- Packaged tray-first startup: PASS.
- High-clarity annotation UI: PASS.
- Note -> Save -> toolbar -> Review baseline flow: PASS.
- Send dropdown visible in annotation toolbar: PASS.
- Send dropdown visible in Review: PASS.
- Dropdown choices Codex / ChatGPT desktop / ChatGPT web / manual paste: PASS.
- Toolbar route persistence through Review: PASS.
- Clipboard/manual-paste fallback: PASS.
- Windows 11 modern right-click menu exposes Show more options: PASS.
- Classic background menu shows Annota as the first item: PASS.
- Shell command registered to the packaged EXE with `--annotate`: PASS.
- Right-click Show more options -> Annota opened Annotation Mode: PASS.
- Existing tray process received the right-click request in the same PID: PASS.
- No duplicate Annota tray icon after forwarded launch: PASS.
- Real Codex/ChatGPT composer insertion: NOT TESTED because no usable target window was available.
- 125%/150%/200% DPI, 1440p/4K, mixed-DPI multi-monitor, and negative-coordinate monitor matrix: NOT TESTED.

## Windows 11 acceptance results - v0.2.1 annotation flow - 2026-08-16
Environment: Windows 11 VM, 1470x923 logical desktop, 100% scaling.

- Fresh packaged EXE startup: PASS.
- Comment card actions `Cancel / + New Annotation / Auto Send / dropdown`: PASS.
- Comment card width/controls with no clipping at tested resolution: PASS.
- First comment saved with + New Annotation and card closed immediately: PASS.
- Second selection opened marker/comment card number 2: PASS.
- First annotation/comment remained available after creating the second annotation: PASS.
- Manual route selection changed primary button from Auto Send to Send to Codex without opening Review or sending: PASS.
- Clicking Send to Codex from the comment card opened Review rather than inserting a payload: PASS.
- Review displayed complete screenshot preview and both numbered comments: PASS.
- Review preserved the selected Send to Codex route: PASS.
- Review dropdown reset the route to Auto Send: PASS.
- Final Auto Send from Review closed the overlay and invoked the existing Annota notification/fallback path: PASS.
- No payload insertion occurred before Review confirmation: PASS.
- Live evidence screenshot: `C:\Projects\QA-Captures\annota-v020-review-flow.png`.
- Automated regression suite before final lifecycle/doc additions: 29 tests PASS.

## Manual acceptance sequence
1. Start Annota and verify tray-only idle state.
2. Test Windows right-click -> Show more options -> Annota and confirm the same tray process opens Annotation Mode.
3. Press Alt+Q over a target application.
4. Select a region, resize it, move it, and type a comment.
5. Click + New Annotation and verify the first comment is saved while selection mode resumes immediately.
6. Create at least one more annotation and comment.
7. Choose a manual destination and verify only the button label changes.
8. Click the destination-aware button and verify Review opens before any payload insertion.
9. Compare screenshot markers to every numbered comment.
10. Use Review + New Annotation and confirm annotation selection resumes.
11. Reopen Review and reset the route to Auto Send.
12. Test final Auto Send with Codex + ChatGPT targets open together.
13. Test each manual destination override.
14. Close Codex/ChatGPT and repeat to verify clipboard fallback.
15. Test Escape/cancel at every stage and verify a cancelled session resets to Auto Send.
16. Test shortcut change/reset/conflict/pause.
17. Build one-folder EXE locally and repeat the workflow from the packaged EXE.


## macOS recovery QA - v0.2.2 - 2026-08-16
Reason: v0.2.1 built successfully but failed physical-Mac use. A successful DMG build alone is no longer accepted as evidence that the app works.

Changes required before the next production Mac release:
- Keep the QSystemTrayIcon context menu alive for the full process lifetime (`self.tray_menu`).
- Show a visible macOS setup window on first run and whenever Screen Recording permission is missing; Accessibility remains an automatic-paste permission, not a Quick Capture prerequisite.
- Provide Start Annotation without relying on Option+Q.
- Preflight/request Screen Recording before capture rather than silently producing a bad capture.
- Do not require Accessibility for Quick Capture. Preflight/request Accessibility/Post Event permission only for native Quartz automatic paste.
- Provide direct links to macOS Privacy & Security panes.
- Support macOS Start at login with a per-user LaunchAgent.
- Preserve safe clipboard fallback if a target cannot be focused or permissions are incomplete.
- Add native macOS running-app classification for Codex/ChatGPT and safe source-browser reuse for an explicit web route.
- Run packaged self-test and launch smoke test on the GitHub Apple Silicon runner before DMG publication.

Current local source gate: Ruff lint/format PASS; Python compile PASS; 57 tests PASS on Windows. Physical-Mac acceptance remains required before converting the RC into a production release.


## macOS Quick Capture recovery QA - v0.2.2
- Physical-Mac feedback: RC 5 exposed no convenient Settings path and Option+Q did not activate capture.
- Setup window now includes a direct Settings button.
- Settings names the field Quick Capture Shortcut and applies changes without restarting.
- macOS capture activation now prefers a bundled native Swift/Carbon `RegisterEventHotKey` helper instead of pynput keyboard monitoring.
- Accessibility is no longer treated as a prerequisite for the capture shortcut; it remains relevant to automatic paste.
- GitHub Apple Silicon QA must compile the helper, successfully register Option+Q, package the helper inside Annota.app, pass runtime self-test, pass app launch smoke test, sign the bundle, build the DMG, and generate SHA-256 before another RC is published.


## macOS automatic-send recovery QA - v0.2.2
- Physical-Mac feedback: permissions could appear granted while automatic send still failed or appeared to do nothing.
- macOS automatic paste no longer uses pynput; it posts native Quartz `Command+V` keyboard events.
- Accessibility/Post Event permission is checked immediately before automatic insertion.
- Destination activation is given a short settling delay before the screenshot paste is attempted.
- Screenshot paste and notes paste are handled separately, and each reports failure instead of silently continuing.
- When automatic insertion is unavailable, PNG/TXT/JSON remain local and the annotation is copied for manual paste.
- After a successful macOS paste request, notes remain on the clipboard because macOS cannot reliably confirm that the destination accepted synthetic input.
- Apple Events are not used, so Automation permission is not part of the required Annota permission set.
- Automated regression coverage includes denied permission, Quartz Command+V event construction/posting, native backend routing, setup fallback status, and fail-safe source contracts.
