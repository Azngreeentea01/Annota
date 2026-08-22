import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect, QSettings
from PySide6.QtWidgets import QApplication, QPushButton

import main


def _app():
    return QApplication.instance() or QApplication([])


def _overlay(tmp_path):
    _app()
    settings = QSettings(str(tmp_path / "annota.ini"), QSettings.IniFormat)
    overlay = main.AnnotationOverlay(settings)
    overlay.annotations = [main.Annotation(1, (10, 10, 40, 40), "first")]
    overlay._annota_annotation_frames = [
        {
            "frame_id": 0,
            "snapshot": overlay.snapshot.copy(),
            "rect": QRect(10, 10, 40, 40),
            "dpr": overlay.dpr,
            "screen_geometry": QRect(overlay.screen_geometry),
        }
    ]
    return overlay


def test_completed_session_reset_clears_all_old_annotation_state(tmp_path):
    overlay = _overlay(tmp_path)
    overlay.pending_rect = QRect(5, 5, 20, 20)
    overlay.current_rect = QRect(5, 5, 20, 20)

    main._reset_completed_session(overlay)

    assert overlay._annota_session_completed is True
    assert overlay.annotations == []
    assert overlay._annota_annotation_frames == []
    assert overlay.pending_rect is None
    assert overlay.current_rect is None
    overlay.close()


def test_note_card_manual_paste_finishes_directly_instead_of_opening_review():
    _app()
    card = main.NoteCard(2)
    manual = next(
        button for button in card.findChildren(QPushButton) if button.text() == "Manual Paste"
    )
    manual_notes = []
    reviews = []
    card.manualPasteRequested.connect(manual_notes.append)
    card.reviewRequested.connect(reviews.append)
    card.editor.setPlainText("finish this session")

    manual.click()

    assert manual_notes == ["finish this session"]
    assert reviews == []
    card.close()


def test_forced_manual_paste_route_is_active_when_payload_is_emitted(monkeypatch):
    captured = []

    class Emitter:
        def emit(self, *_args):
            captured.append(main._SEND_ROUTE_OVERRIDE)

    class FakeOverlay:
        def __init__(self):
            self.annotations = [main.Annotation(1, (1, 1, 10, 10), "note")]
            self.finishedCapture = Emitter()
            self._annota_annotation_frames = []
            self.pending_rect = None
            self.current_rect = None
            self.drag_start = None
            self.interaction = None
            self.interaction_start = None
            self.interaction_rect = None
            self.note_card = None
            self.review_card = None
            self.toolbar = None

        def _build_payload(self):
            return "image.png", "note", "meta.json"

        def close(self):
            pass

    monkeypatch.setattr(main, "_diagnostic_event", lambda *_args, **_kwargs: None)
    overlay = FakeOverlay()
    main._send_overlay_without_review(overlay, force_route="clipboard")
    assert captured == ["clipboard"]


def test_completed_overlay_is_not_treated_as_paused_session_contract():
    source = (__import__("pathlib").Path(__file__).resolve().parents[1] / "main.py").read_text(
        encoding="utf-8"
    )
    assert 'not getattr(self.overlay, "_annota_session_completed", False)' in source
    assert "_reset_completed_session(overlay)" in source
    assert "_reset_completed_session(self)" in source
    assert "manualPasteRequested.emit(note)" in source
    assert "def _save_and_manual_paste" in source
