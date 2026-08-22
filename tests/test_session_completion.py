import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect, QSettings
from PySide6.QtWidgets import QApplication

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


def test_completed_overlay_is_not_treated_as_paused_session_contract():
    source = (__import__("pathlib").Path(__file__).resolve().parents[1] / "main.py").read_text(
        encoding="utf-8"
    )
    assert 'not getattr(self.overlay, "_annota_session_completed", False)' in source
    assert "_reset_completed_session(overlay)" in source
    assert "_reset_completed_session(self)" in source
