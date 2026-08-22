import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QComboBox

import main
from target_routing import SUPPORTED_TARGETS


def _app():
    return QApplication.instance() or QApplication([])


def test_settings_exposes_persistent_default_send_destination(tmp_path):
    _app()
    settings = QSettings(str(tmp_path / "annota.ini"), QSettings.IniFormat)
    settings.setValue(main._annota_default_send_route_key, "gemini")

    dialog = main.SettingsDialog(settings)
    combos = [
        box for box in dialog.findChildren(QComboBox) if box.objectName() == "defaultSendRoute"
    ]

    assert len(combos) == 1
    combo = combos[0]
    assert combo.currentData() == "gemini"
    assert combo.itemData(0) == "auto"
    assert combo.itemText(0) == "Auto Send (Recommended)"
    assert [
        (combo.itemData(i), combo.itemText(i)) for i in range(1, 1 + len(SUPPORTED_TARGETS))
    ] == list(SUPPORTED_TARGETS)
    assert combo.count() == 1 + len(SUPPORTED_TARGETS)
    assert all(combo.itemData(i) != "clipboard" for i in range(combo.count()))
    dialog.close()


def test_default_send_route_rejects_unknown_saved_value(tmp_path):
    _app()
    settings = QSettings(str(tmp_path / "annota.ini"), QSettings.IniFormat)
    settings.setValue(main._annota_default_send_route_key, "not-a-target")
    assert main._default_send_route(settings) is None


def test_legacy_clipboard_default_migrates_to_auto(tmp_path):
    _app()
    settings = QSettings(str(tmp_path / "annota.ini"), QSettings.IniFormat)
    settings.setValue(main._annota_default_send_route_key, "clipboard")
    assert main._default_send_route(settings) is None
