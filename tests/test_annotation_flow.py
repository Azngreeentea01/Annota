import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QPushButton, QToolButton

import main


def _app():
    return QApplication.instance() or QApplication([])


def _button(root, text):
    matches = [button for button in root.findChildren(QPushButton) if button.text() == text]
    assert matches, f"Button not found: {text}"
    return matches[0]


def _route_button(root):
    matches = [
        button
        for button in root.findChildren(QToolButton)
        if button.objectName() == "sendRouteButton"
    ]
    assert len(matches) == 1
    return matches[0]


def setup_function(_function):
    main._clear_pending_send_route()


def teardown_function(_function):
    main._clear_pending_send_route()


def test_note_card_new_annotation_saves_comment_without_sending():
    _app()
    card = main.NoteCard(1)
    new_notes = []
    reviews = []
    card.newAnnotationRequested.connect(new_notes.append)
    card.reviewRequested.connect(reviews.append)
    card.editor.setPlainText("Move this button left")

    _button(card, "+ New Annotation").click()

    assert new_notes == ["Move this button left"]
    assert reviews == []
    card.close()


def test_note_card_auto_send_opens_review_path_only():
    _app()
    card = main.NoteCard(1)
    new_notes = []
    reviews = []
    card.newAnnotationRequested.connect(new_notes.append)
    card.reviewRequested.connect(reviews.append)
    card.editor.setPlainText("Increase the spacing")

    _button(card, "Auto Send").click()

    assert reviews == ["Increase the spacing"]
    assert new_notes == []
    assert main._SEND_ROUTE_OVERRIDE is None
    card.close()


def test_send_menu_contains_exact_supported_app_list():
    _app()
    card = main.NoteCard(1)
    route = _route_button(card)
    labels = [action.text() for action in route.menu().actions() if action.text()]
    supported = [
        "Codex",
        "ChatGPT",
        "Claude",
        "Cursor",
        "Visual Studio Code",
        "Windsurf",
        "OpenCode",
    ]
    assert labels[0] == "Auto Send (Recommended)"
    assert labels[1:8] == supported
    assert labels[-1] == "Copy for manual paste"
    assert "Send to ChatGPT web" not in labels
    assert "Send to ChatGPT desktop" not in labels
    card.close()


def test_dropdown_uses_native_arrow_and_is_vertically_aligned():
    _app()
    card = main.NoteCard(1)
    route = _route_button(card)
    send = _button(card, "Auto Send")
    assert route.text() == ""
    assert route.arrowType() == main.Qt.DownArrow
    assert abs(route.height() - send.sizeHint().height()) <= 2 or route.height() >= 34
    card.close()


def test_manual_route_selection_switches_button_to_send_without_triggering_review():
    _app()
    card = main.NoteCard(1)
    reviews = []
    card.reviewRequested.connect(reviews.append)
    card.editor.setPlainText("Use a larger icon")

    route = _route_button(card)
    claude_action = next(action for action in route.menu().actions() if action.text() == "Claude")
    claude_action.trigger()

    send = _button(card, "Send")
    assert send.toolTip() == "Send only to Claude."
    assert send.property("annotaSendRoute") == "claude"
    assert main._PENDING_SEND_ROUTE == "claude"
    assert reviews == []
    card.close()


def test_selected_route_carries_into_review_and_only_review_commits_it():
    _app()
    note_card = main.NoteCard(1)
    route = _route_button(note_card)
    vscode_action = next(
        action for action in route.menu().actions() if action.text() == "Visual Studio Code"
    )
    vscode_action.trigger()
    assert _button(note_card, "Send")
    assert main._PENDING_SEND_ROUTE == "vscode"
    assert main._SEND_ROUTE_OVERRIDE is None

    preview = QPixmap(640, 360)
    preview.fill()
    review = main.ReviewCard([main.Annotation(1, (10, 20, 100, 80), "Fix alignment")], preview)
    sent = []
    review.sendRequested.connect(lambda: sent.append(True))

    send = _button(review, "Send")
    assert send.toolTip() == "Send only to Visual Studio Code."
    assert send.property("annotaSendRoute") == "vscode"
    assert main._SEND_ROUTE_OVERRIDE is None

    send.click()

    assert sent == [True]
    assert main._SEND_ROUTE_OVERRIDE == "vscode"
    review.close()
    note_card.close()


def test_review_can_reset_manual_route_back_to_auto_send():
    _app()
    preview = QPixmap(640, 360)
    preview.fill()
    review = main.ReviewCard([main.Annotation(1, (1, 2, 30, 40), "Test")], preview)
    route = _route_button(review)
    cursor_action = next(action for action in route.menu().actions() if action.text() == "Cursor")
    cursor_action.trigger()
    send = _button(review, "Send")
    assert send.toolTip() == "Send only to Cursor."
    assert main._PENDING_SEND_ROUTE == "cursor"

    auto_action = next(
        action for action in route.menu().actions() if action.text() == "Auto Send (Recommended)"
    )
    auto_action.trigger()

    auto_send = _button(review, "Auto Send")
    assert auto_send.toolTip() == "Automatically send to the app active when annotation started."
    assert auto_send.property("annotaSendRoute") == "auto"
    assert main._PENDING_SEND_ROUTE is None
    assert main._SEND_ROUTE_OVERRIDE is None
    review.close()


def test_review_footer_uses_new_annotation_not_add_another():
    _app()
    preview = QPixmap(640, 360)
    preview.fill()
    review = main.ReviewCard([main.Annotation(1, (1, 2, 30, 40), "Test")], preview)
    labels = {button.text() for button in review.findChildren(QPushButton)}
    assert "+ New Annotation" in labels
    assert "+ Add another" not in labels
    review.close()


def test_v022_review_gate_and_session_reset_source_contract():
    core_source = (Path(__file__).resolve().parents[1] / "annota_core.py").read_text(
        encoding="utf-8"
    )
    entry_source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    assert main.APP_VERSION == "0.2.3"
    assert "def closeEvent(self, event):" in core_source
    assert "_clear_pending_send_route()" in core_source
    assert "if not self.review_card or not self.review_card.isVisible():" in core_source
    assert "self._show_review()" in core_source
    assert "_install_routing_extension()" in entry_source
