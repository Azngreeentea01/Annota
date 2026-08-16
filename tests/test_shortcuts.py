import platform

import main


def test_default_shortcut_is_platform_specific():
    expected = "Option+Q" if platform.system() == "Darwin" else "Alt+Q"
    assert main.default_shortcut() == expected


def test_normalize_shortcut_accepts_alt_q():
    expected = "Option+Q" if platform.system() == "Darwin" else "Alt+Q"
    assert main.normalize_shortcut("Alt + Q") == expected


def test_normalize_shortcut_accepts_function_key():
    expected_mod = "Option" if platform.system() == "Darwin" else "Alt"
    assert main.normalize_shortcut("Alt+F8") == f"{expected_mod}+F8"


def test_normalize_shortcut_rejects_single_key():
    assert main.normalize_shortcut("Q") == ""


def test_normalize_shortcut_rejects_unknown_modifier():
    assert main.normalize_shortcut("Hyper+Q") == ""


def test_normalize_shortcut_rejects_out_of_range_function_key():
    assert main.normalize_shortcut("Alt+F25") == ""


def test_pynput_mapping():
    seq = "Option+Q" if platform.system() == "Darwin" else "Alt+Q"
    assert main.to_pynput_hotkey(seq) == "<alt>+q"


def test_annotation_dataclass_keeps_note_and_rect():
    ann = main.Annotation(1, (10, 20, 300, 200), "Fix spacing")
    assert ann.index == 1
    assert ann.rect == (10, 20, 300, 200)
    assert ann.note == "Fix spacing"
