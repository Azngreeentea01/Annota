# Annota v0.2.1

Annota v0.2.1 improves the annotation-to-review workflow and adds downloadable builds for Windows x64 and macOS ARM64.

## Highlights
- New `+ New Annotation` action saves the current comment and immediately returns to selection mode.
- `Auto Send` is now the default action and always opens Review before any payload insertion.
- Manual destination selection changes the primary button label to the selected route, such as `Send to Codex`.
- Review is the required confirmation gate and shows the full annotated screenshot plus every numbered comment.
- Review can continue with another annotation, cancel, reset to Auto Send, or perform the final destination-aware send.
- `Ctrl+Enter` can no longer bypass Review.
- Route state resets when the full annotation session closes.

## Windows x64
- Native PySide6 one-folder package.
- Windows 11 tray, Alt+Q, context-menu launch, multiple annotations, Review, Auto Send/manual routing and clipboard fallback verified on the project VM.
- Automated suite: 31 tests passing before release packaging.

## macOS ARM64
- Native Apple Silicon build produced on GitHub's `macos-15` ARM64 runner.
- PyInstaller `.app` packaged into a `.dmg` with SHA-256 verification.
- App uses an ad-hoc signature unless a Developer ID certificate is configured; this release is not notarized.
- A physical-Mac acceptance pass is still recommended for Screen Recording, Accessibility, Option+Q, menu-bar behavior, Retina/multi-display behavior, and real Codex/ChatGPT insertion.

## Privacy
Annota remains local-first: no telemetry, account requirement, continuous capture, cloud upload, or background AI. Annota never presses the final chat Send button for the user.
