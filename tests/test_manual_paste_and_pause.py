import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QPushButton

import main


def _app():
    return QApplication.instance() or QApplication([])


def test_note_card_has_manual_paste_button_next_to_send_controls():
    _app()
    card = main.NoteCard(1)
    labels = [b.text() for b in card.findChildren(QPushButton)]
    assert "Auto Send" in labels
    assert "Manual Paste" in labels
    card.close()


def test_review_card_has_manual_paste_button():
    _app()
    annotation = main.Annotation(1, (10, 10, 40, 40), "test")
    card = main.ReviewCard([annotation], QPixmap(120, 80))
    labels = [b.text() for b in card.findChildren(QPushButton)]
    assert "Manual Paste" in labels
    card.close()


def test_escape_pause_contract_preserves_session_and_resume_contract():
    source = (__import__("pathlib").Path(__file__).resolve().parents[1] / "main.py").read_text(
        encoding="utf-8"
    )
    assert "def _pause_annotation_session" in source
    assert "self.hide()" in source
    assert "annotation_session_paused" in source
    assert "def _resume_annotation_session" in source
    assert "self.snapshot = self.screen.grabWindow(0)" in source
    assert "self.overlay.annotations" in source
    assert "_resume_annotation_session(self.overlay)" in source


def test_scroll_session_preserves_frame_for_each_annotation_contract():
    source = (__import__("pathlib").Path(__file__).resolve().parents[1] / "main.py").read_text(
        encoding="utf-8"
    )
    assert "_annota_annotation_frames" in source
    assert "_commit_pending_note_with_frame" in source
    assert "_render_session_composite" in source
    assert 'composite.save(image_path, "PNG")' in source


def test_copy_for_manual_paste_removed_from_route_menu_contract():
    source = (__import__("pathlib").Path(__file__).resolve().parents[1] / "main.py").read_text(
        encoding="utf-8"
    )
    assert 'menu.addAction("Copy for manual paste")' not in source
