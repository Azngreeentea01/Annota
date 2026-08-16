import io
import plistlib
from pathlib import Path

from PySide6.QtWidgets import QApplication, QPushButton

import main

ROOT = Path(__file__).resolve().parents[1]


def _app():
    return QApplication.instance() or QApplication([])


def test_macos_app_classification_contract():
    assert main.classify_macos_app({"name": "Codex", "bundle_id": "com.openai.codex"}) == "codex"
    assert (
        main.classify_macos_app({"name": "ChatGPT", "bundle_id": "com.openai.chat"})
        == "chatgpt_desktop"
    )
    assert (
        main.classify_macos_app({"name": "Safari", "bundle_id": "com.apple.Safari"})
        == "chatgpt_web"
    )
    assert main.classify_macos_app({"name": "Finder", "bundle_id": "com.apple.finder"}) is None


def test_manual_web_route_can_reuse_source_browser(monkeypatch):
    monkeypatch.setattr(main, "is_macos", lambda: True)
    source = {"pid": 44, "name": "Safari", "bundle_id": "com.apple.Safari"}
    assert main.macos_find_chat_target("chatgpt_web", source) == source


def test_non_macos_permission_status_is_ready():
    status = main.macos_permission_status()
    if not main.is_macos():
        assert status == {"screen_recording": True, "accessibility": True, "post_events": True}


def test_configure_startup_routes_to_macos_helper(monkeypatch):
    called = []
    monkeypatch.setattr(main, "is_macos", lambda: True)
    monkeypatch.setattr(main, "configure_macos_startup", lambda enabled: called.append(enabled))
    main.configure_startup(True)
    assert called == [True]


def test_macos_startup_source_mode_includes_main_script(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "is_macos", lambda: True)
    monkeypatch.setattr(main.Path, "home", classmethod(lambda _cls: tmp_path))
    monkeypatch.delattr(main.sys, "frozen", raising=False)

    main.configure_macos_startup(True)

    plist_path = tmp_path / "Library" / "LaunchAgents" / "net.softwify.annota.plist"
    with plist_path.open("rb") as handle:
        data = plistlib.load(handle)
    assert data["ProgramArguments"] == [
        str(Path(main.sys.executable).resolve()),
        str(Path(main.__file__).resolve()),
    ]

    main.configure_macos_startup(False)
    assert not plist_path.exists()


def test_macos_native_hotkey_supported_keys():
    assert main.macos_hotkey_supported("Option+Q")
    assert main.macos_hotkey_supported("Cmd+Shift+A")
    assert main.macos_hotkey_supported("Ctrl+Option+F8")
    assert main.macos_hotkey_supported("Option+9")
    assert not main.macos_hotkey_supported("Option+F21")
    assert not main.macos_hotkey_supported("Option+;")


def test_stale_native_hotkey_monitor_cannot_override_current_process():
    class FakeProcess:
        def __init__(self, error=""):
            self.stdout = io.StringIO("")
            self.stderr = io.StringIO(error)

        def poll(self):
            return 1

    hotkey = main.GlobalHotkey(lambda: None)
    old_process = FakeProcess("ERROR stale helper failure")
    current_process = FakeProcess()
    hotkey.mac_process = current_process
    hotkey.mac_ready = True
    hotkey.last_error = ""
    hotkey._generation = 8

    hotkey._monitor_macos_helper(old_process, 7)

    assert hotkey.mac_process is current_process
    assert hotkey.mac_ready is True
    assert hotkey.last_error == ""


def test_macos_setup_has_settings_and_start_annotation_controls():
    _app()
    dialog = main.MacSetupDialog("Option+Q")
    labels = {button.text() for button in dialog.findChildren(QPushButton)}
    assert "Settings" in labels
    assert "Start Annotation" in labels
    assert "Refresh" in labels
    assert "Allow Screen Recording" in labels
    dialog.close()


def test_native_hotkey_swift_source_contract():
    source = (ROOT / "tools" / "annota_hotkey.swift").read_text(encoding="utf-8")
    assert "RegisterEventHotKey" in source
    assert "kEventHotKeyPressed" in source
    assert 'print("READY \\(shortcut)")' in source
    assert 'print("TRIGGER")' in source
    assert '"Q": 12' in source


def test_macos_runtime_reliability_source_contract():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "0.2.2"' in source
    assert "self.tray_menu = QMenu()" in source
    assert "CGPreflightScreenCaptureAccess" in source
    assert "AXIsProcessTrusted" in source
    assert "Start Annotation" in source
    assert "Quick Capture Shortcut" in source
    assert "settingsRequested = Signal()" in source
    assert "HOTKEY_HELPER_PATH" in source
    assert "subprocess.Popen" in source
    assert "Active (native macOS)" in source
    assert "macos/setup_seen" in source
    assert "Native shortcut helper stopped unexpectedly" in source
    assert "--self-test" in source
    assert "--smoke-test" in source
