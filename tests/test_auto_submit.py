import sys
from pathlib import Path
from types import SimpleNamespace

import main


def test_auto_send_entrypoint_installs_submit_hook():
    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    assert "core.AnnotaApp._send_to_current_chat = _send_to_current_chat_with_auto_submit" in source
    assert "core.paste_shortcut = _paste_shortcut_with_auto_submit" in source
    assert '_SEND_SESSION["paste_count"] == 2' in source
    assert "core.QTimer.singleShot(220, _finish_auto_send)" in source


def test_macos_submit_posts_return_key(monkeypatch):
    events = []
    posts = []

    def create_event(_source, key_code, is_down):
        event = {"key_code": key_code, "is_down": is_down}
        events.append(event)
        return event

    def post_event(tap, event):
        posts.append((tap, event.copy()))

    quartz = SimpleNamespace(
        kCGHIDEventTap=0,
        CGEventCreateKeyboardEvent=create_event,
        CGEventPost=post_event,
    )
    monkeypatch.setitem(sys.modules, "Quartz", quartz)
    monkeypatch.setattr(main, "is_macos", lambda: True)

    ok, error = main._annota_submit_shortcut()

    assert ok
    assert error == ""
    assert [(event["key_code"], event["is_down"]) for event in events] == [
        (36, True),
        (36, False),
    ]
    assert len(posts) == 2


def test_submit_failure_keeps_manual_action_clear(monkeypatch):
    monkeypatch.setattr(main, "is_macos", lambda: False)
    monkeypatch.setattr(main, "keyboard", None)

    ok, error = main._annota_submit_shortcut()

    assert not ok
    assert error == "Keyboard backend unavailable"
