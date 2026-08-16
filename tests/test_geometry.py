from PySide6.QtCore import QRect

import main


def test_annotation_rect_shape_is_stable():
    ann = main.Annotation(2, (25, 40, 200, 120), "Resize card")
    rect = QRect(*ann.rect)
    assert rect.x() == 25
    assert rect.y() == 40
    assert rect.width() == 200
    assert rect.height() == 120


def test_shortcut_conflict_helper_returns_bool():
    assert isinstance(main.shortcut_conflicts(main.default_shortcut()), bool)
