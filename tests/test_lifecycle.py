import queue

from PySide6.QtWidgets import QSystemTrayIcon

import main


def _clear_command_queue():
    while True:
        try:
            main._COMMAND_QUEUE.get_nowait()
        except queue.Empty:
            return


class FakeController:
    def __init__(self):
        self.calls = []

    def activate_annotation(self, force=False):
        self.calls.append(("annotate", force))

    def open_macos_setup(self):
        self.calls.append(("mac_setup", True))

    def open_settings(self):
        self.calls.append(("settings", True))


def test_macos_menu_bar_click_preserves_context_menu(monkeypatch):
    monkeypatch.setattr(main, "is_macos", lambda: True)
    assert not main.tray_click_starts_annotation(QSystemTrayIcon.Trigger)


def test_windows_tray_trigger_starts_annotation(monkeypatch):
    monkeypatch.setattr(main, "is_macos", lambda: False)
    assert main.tray_click_starts_annotation(QSystemTrayIcon.Trigger)


def test_show_command_opens_existing_macos_setup(monkeypatch):
    _clear_command_queue()
    controller = FakeController()
    monkeypatch.setattr(main, "is_macos", lambda: True)
    main._COMMAND_QUEUE.put("show")

    main._drain_instance_commands(controller)

    assert controller.calls == [("mac_setup", True)]


def test_show_command_opens_settings_on_windows(monkeypatch):
    _clear_command_queue()
    controller = FakeController()
    monkeypatch.setattr(main, "is_macos", lambda: False)
    main._COMMAND_QUEUE.put("show")

    main._drain_instance_commands(controller)

    assert controller.calls == [("settings", True)]


def test_annotate_command_forces_existing_instance_capture():
    _clear_command_queue()
    controller = FakeController()
    main._COMMAND_QUEUE.put("annotate")

    main._drain_instance_commands(controller)

    assert controller.calls == [("annotate", True)]
