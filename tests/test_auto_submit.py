from pathlib import Path


def test_auto_send_does_not_submit_the_chat_message():
    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    assert "_submit_shortcut" not in source
    assert "keyboard.Key.enter" not in source
    assert "CGEventCreateKeyboardEvent" not in source
    assert "core.paste_shortcut =" not in source
    assert "core.AnnotaApp._send_to_current_chat =" not in source


def test_native_send_flow_stops_after_inserting_content():
    source = (Path(__file__).resolve().parents[1] / "annota_core.py").read_text(encoding="utf-8")
    assert "Screenshot and notes are ready. Review them in the composer" in source
    assert "Screenshot and notes inserted. Review them before sending." in source
