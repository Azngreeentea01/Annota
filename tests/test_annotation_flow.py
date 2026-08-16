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
    matches = root.findChildren(QToolButton)
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


def test_manual_route_selection_changes_button_without_triggering_review():
    _app()
    card = main.NoteCard(1)
    reviews = []
    card.reviewRequested.connect(reviews.append)
    card.editor.setPlainText("Use a larger icon")

    route = _route_button(card)
    codex_action = next(action for action in route.menu().actions() if action.text() == "Send to Codex")
    codex_action.trigger()

    assert _button(card, "Send to Codex")
    assert main._PENDING_SEND_ROUTE == "codex"
    assert reviews == []
    card.close()


def test_selected_route_carries_into_review_and_only_review_commits_it():
    _app()
    note_card = main.NoteCard(1)
    route = _route_button(note_card)
    web_action = next(action for action in route.menu().actions() if action.text() == "Send to ChatGPT web")
    web_action.trigger()
    assert main._PENDING_SEND_ROUTE == "chatgpt_web"
    assert main._SEND_ROUTE_OVERRIDE is None

    preview = QPixmap(640, 360)
    preview.fill()
    review = main.ReviewCard([main.Annotation(1, (10, 20, 100, 80), "Fix alignment")], preview)
    sent = []
    review.sendRequested.connect(lambda: sent.append(True))

    assert _button(review, "Send to ChatGPT Web")
    assert main._SEND_ROUTE_OVERRIDE is None

    _button(review, "Send to ChatGPT Web").click()

    assert sent == [True]
    assert main._SEND_ROUTE_OVERRIDE == "chatgpt_web"
    review.close()
    note_card.close()


def test_review_can_reset_manual_route_back_to_auto_send():
    _app()
    main._PENDING_SEND_ROUTE = "codex"
    preview = QPixmap(640, 360)
    preview.fill()
    review = main.ReviewCard([main.Annotation(1, (1, 2, 30, 40), "Test")], preview)
    assert _button(review, "Send to Codex")

    route = _route_button(review)
    auto_action = next(action for action in route.menu().actions() if action.text() == "Auto Send (Recommended)")
    auto_action.trigger()

    assert _button(review, "Auto Send")
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


def test_v021_review_gate_and_session_reset_source_contract():
    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    assert main.APP_VERSION == "0.2.1"
    assert "def closeEvent(self, event):" in source
    assert "_clear_pending_send_route()" in source
    assert "if not self.review_card or not self.review_card.isVisible():" in source
    assert "self._show_review()" in source
