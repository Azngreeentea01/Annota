import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

import main


def _app():
    return QApplication.instance() or QApplication([])


def test_approved_note_card_has_wide_unclipped_action_row():
    _app()
    card = main.NoteCard(1)
    assert card.width() == 820
    buttons = {b.text(): b for b in card.findChildren(QPushButton)}
    assert buttons["Cancel"].width() == 112
    assert buttons["New Annotation"].width() == 178
    assert buttons["Auto Send"].width() == 158
    assert buttons["Manual Paste"].width() == 150
    assert buttons["Manual Paste"].objectName() == "manualPasteButton"
    route = card.findChild(main.QToolButton, "sendRouteButton")
    assert route.width() == 46
    assert route.height() == 48
    assert all(
        b.height() == 48
        for b in [
            buttons["Cancel"],
            buttons["New Annotation"],
            buttons["Auto Send"],
            buttons["Manual Paste"],
        ]
    )
    card.close()


def test_send_menu_has_icons_for_every_supported_target():
    _app()
    card = main.NoteCard(1)
    route = card.findChild(main.QToolButton, "sendRouteButton")
    actions = [a for a in route.menu().actions() if a.text()]
    assert actions[0].text() == "Send to"
    assert not actions[0].isEnabled()
    assert actions[1].text() == "Auto Send"
    assert not actions[1].icon().isNull()
    expected = [
        "ChatGPT",
        "Codex",
        "Claude",
        "Cursor",
        "Visual Studio Code",
        "Windsurf",
        "OpenCode",
        "Cline",
        "Roo Code",
        "GitHub Copilot",
        "Gemini",
    ]
    assert [a.text() for a in actions[2:]] == expected
    assert all(not a.icon().isNull() for a in actions[2:])
    card.close()
