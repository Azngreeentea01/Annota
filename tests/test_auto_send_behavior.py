import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QCheckBox

import main


def _app():
    return QApplication.instance() or QApplication([])


def test_preserved_opencode_source_is_used_after_activation_started():
    main._ANNOTA_CAPTURE_SOURCE_TARGET = {
        "hwnd": 77,
        "pid": 777,
        "route": "opencode",
        "executable": r"C:\Users\Test\OpenCode.exe",
        "title": "OpenCode - project",
    }
    assert main.active_window_context() == ("OpenCode.exe", "OpenCode - project")


def test_activation_captures_source_before_overlay_constructor_contract():
    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    assert "core.AnnotaApp.activate_annotation = _activate_annotation_with_source" in source
    assert "core._ANNOTA_CAPTURE_SOURCE_TARGET = target" in source
    assert "if preserved:" in source


def test_outgoing_chat_message_hides_machine_metadata_contract():
    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    for prefix in ("Application:", "Window:", "Display:", "DPI scale:", "Timestamp:"):
        assert prefix in source
    assert (
        'hidden_prefixes = ("Application:", "Window:", "Display:", "DPI scale:", "Timestamp:")'
        in source
    )
    assert "if line.startswith(hidden_prefixes):" in source


def test_ai_instruction_checkbox_defaults_off(tmp_path):
    _app()
    settings = QSettings(str(tmp_path / "annota.ini"), QSettings.IniFormat)
    dialog = main.SettingsDialog(settings)
    matches = [
        box for box in dialog.findChildren(QCheckBox) if box.objectName() == "includeAiInstruction"
    ]
    assert len(matches) == 1
    assert not matches[0].isChecked()
    assert main._annota_ai_implementation_instruction in matches[0].toolTip()
    dialog.close()


def test_ai_instruction_setting_key_and_payload_are_opt_in():
    assert main._annota_include_ai_instruction_key == "behavior/include_ai_instruction"
    instruction = main._annota_ai_implementation_instruction
    assert instruction == (
        "Use the highlighted regions as the visual source of truth. Inspect the relevant code, "
        "implement these fixes, build and test locally, and visually verify the result."
    )
    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    assert "settings.value(INCLUDE_AI_INSTRUCTION_KEY, False, type=bool)" in source
