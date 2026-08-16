import sys
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

import main


def _app():
    return QApplication.instance() or QApplication([])


class _FakeSettings:
    def __init__(self):
        self.values = {}

    def value(self, key, default=None, type=None):
        value = self.values.get(key, default)
        return type(value) if type is not None else value

    def setValue(self, key, value):
        self.values[key] = value


def test_macos_automatic_paste_ready_accepts_either_permission(monkeypatch):
    monkeypatch.setattr(main, "is_macos", lambda: True)
    assert not main.macos_automatic_paste_ready(
        {"screen_recording": True, "accessibility": False, "post_events": False}
    )
    assert main.macos_automatic_paste_ready(
        {"screen_recording": True, "accessibility": True, "post_events": False}
    )
    assert main.macos_automatic_paste_ready(
        {"screen_recording": True, "accessibility": False, "post_events": True}
    )


def test_macos_native_paste_refuses_when_permission_is_unavailable(monkeypatch):
    monkeypatch.setattr(main, "is_macos", lambda: True)
    monkeypatch.setattr(
        main,
        "macos_permission_status",
        lambda: {"screen_recording": True, "accessibility": False, "post_events": False},
    )

    ok, error = main.macos_post_paste_shortcut()

    assert not ok
    assert "Accessibility permission" in error


def test_macos_native_paste_posts_command_v_with_quartz(monkeypatch):
    events = []
    posts = []

    def create_event(_source, key_code, is_down):
        event = {"key_code": key_code, "is_down": is_down, "flags": None}
        events.append(event)
        return event

    def set_flags(event, flags):
        event["flags"] = flags

    def post_event(tap, event):
        posts.append((tap, event.copy()))

    quartz = SimpleNamespace(
        kCGEventFlagMaskCommand=0x100000,
        kCGHIDEventTap=0,
        CGEventCreateKeyboardEvent=create_event,
        CGEventSetFlags=set_flags,
        CGEventPost=post_event,
    )
    monkeypatch.setitem(sys.modules, "Quartz", quartz)
    monkeypatch.setattr(main, "is_macos", lambda: True)
    monkeypatch.setattr(
        main,
        "macos_permission_status",
        lambda: {"screen_recording": True, "accessibility": True, "post_events": True},
    )

    ok, error = main.macos_post_paste_shortcut()

    assert ok
    assert error == ""
    assert [(event["key_code"], event["is_down"]) for event in events] == [(9, True), (9, False)]
    assert all(event["flags"] == quartz.kCGEventFlagMaskCommand for event in events)
    assert len(posts) == 2
    assert all(tap == quartz.kCGHIDEventTap for tap, _event in posts)


def test_paste_shortcut_routes_to_native_macos_backend(monkeypatch):
    monkeypatch.setattr(main, "is_macos", lambda: True)
    monkeypatch.setattr(main, "macos_post_paste_shortcut", lambda: (True, ""))
    assert main.paste_shortcut() == (True, "")


def test_macos_setup_reports_automatic_send_fallback(monkeypatch):
    _app()
    monkeypatch.setattr(
        main,
        "macos_permission_status",
        lambda: {"screen_recording": True, "accessibility": False, "post_events": False},
    )
    monkeypatch.setattr(main, "is_macos", lambda: True)

    dialog = main.MacSetupDialog("Option+Q")

    assert "Clipboard fallback" in dialog.send_status.text()
    assert "Permission required" in dialog.access_status.text()
    dialog.close()


def test_macos_settings_keeps_clipboard_fallback_enabled(monkeypatch):
    _app()
    monkeypatch.setattr(main, "is_macos", lambda: True)

    dialog = main.SettingsDialog(_FakeSettings())

    assert "Keep notes on clipboard" in dialog.clear_after.text()
    assert dialog.clear_after.isChecked()
    assert not dialog.clear_after.isEnabled()
    dialog.close()


def test_macos_send_source_contract_is_fail_safe():
    source = Path(main.__file__).read_text(encoding="utf-8")
    assert "CGEventPost" in source
    assert "_copy_for_manual_paste" in source
    assert "Paste requested in current chat" in source
    assert "notes remain on the clipboard as a fallback" in source
