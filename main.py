"""Annota application entry point with supported-app Auto Send integration.

The established application stays in ``annota_core``. This module installs the
small routing extension before starting it, keeping target detection isolated
and testable without disturbing the annotation workflow.
"""

from __future__ import annotations

import ctypes
import os
import sys
from contextlib import suppress
from pathlib import Path

from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QMenu, QSizePolicy, QToolButton

import annota_core as core
from target_routing import (
    SUPPORTED_TARGETS,
    TARGET_ORDER,
    choose_target_record,
    classify_macos_target,
    classify_windows_target,
    target_description,
    target_label,
)
from ui_style import build_app_style

core.APP_STYLE = build_app_style(core.APP_STYLE)

_ORIGINAL_OVERLAY_INIT = core.AnnotationOverlay.__init__
_ORIGINAL_BUILD_PAYLOAD = core.AnnotationOverlay._build_payload
_ORIGINAL_SETTINGS_INIT = core.SettingsDialog.__init__
_ORIGINAL_SETTINGS_SAVE = core.SettingsDialog._save
_ORIGINAL_ACTIVATE_ANNOTATION = core.AnnotaApp.activate_annotation
SKIP_MULTI_REVIEW_KEY = "behavior/skip_review_multiple"
INCLUDE_AI_INSTRUCTION_KEY = "behavior/include_ai_instruction"
DEFAULT_SEND_ROUTE_KEY = "behavior/default_send_route"
AI_IMPLEMENTATION_INSTRUCTION = (
    "Use the highlighted regions as the visual source of truth. Inspect the relevant code, "
    "implement these fixes, build and test locally, and visually verify the result."
)


def _windows_frontmost_target() -> dict:
    if os.name != "nt":
        return {}
    try:
        user32 = ctypes.windll.user32
        hwnd = int(user32.GetForegroundWindow() or 0)
        if not hwnd:
            return {}
        length = user32.GetWindowTextLengthW(hwnd)
        title_buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buffer, length + 1)
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        executable = core._process_image_path(int(pid.value))
        route = classify_windows_target(title_buffer.value, executable)
        return {
            "hwnd": hwnd,
            "title": title_buffer.value or "Unknown window",
            "pid": int(pid.value),
            "executable": executable,
            "route": route,
        }
    except Exception:
        return {}


def _capture_source_target() -> dict:
    if core.is_macos():
        target = dict(core.macos_frontmost_app() or {})
        target["route"] = classify_macos_target(target)
        return target
    if os.name == "nt":
        return _windows_frontmost_target()
    return {}


def _source_context(target: dict) -> tuple[str, str]:
    if core.is_macos():
        return target.get("name", "macOS"), "Active macOS app"
    executable = str(target.get("executable", ""))
    process_name = Path(executable).name if executable else f"PID {target.get('pid', 0)}"
    return process_name, target.get("title", "Unknown window")


def _active_window_context() -> tuple[str, str]:
    """Return the source captured before the overlay took focus.

    The overlay constructor calls this function after annotation activation has
    already begun. Re-querying the foreground window here can therefore record
    Annota or another transient window instead of the app the user was using.
    """
    preserved = dict(getattr(core, "_ANNOTA_CAPTURE_SOURCE_TARGET", {}) or {})
    if preserved:
        return _source_context(preserved)
    target = _capture_source_target()
    core._ANNOTA_CAPTURE_SOURCE_TARGET = target
    return _source_context(target)


def _activate_annotation_with_source(self, force: bool = False):
    """Capture the foreground app before any overlay/UI can steal focus."""
    if not (self.overlay and self.overlay.isVisible()):
        target = _capture_source_target()
        core._ANNOTA_CAPTURE_SOURCE_TARGET = target
        self.last_source_target = dict(target)
        core._diagnostic_event(
            "capture_source_recorded",
            route=target.get("route"),
            pid=target.get("pid"),
            hwnd=target.get("hwnd"),
            title=target.get("title", target.get("name", "")),
        )
    return _ORIGINAL_ACTIVATE_ANNOTATION(self, force)


def _classify_macos_app(target: dict) -> str | None:
    return classify_macos_target(target)


def _macos_find_chat_target(route: str | None = None, source_target: dict | None = None) -> dict:
    if not core.is_macos() or route == "clipboard":
        return {}
    source = dict(source_target or core._ANNOTA_CAPTURE_SOURCE_TARGET or {})
    source["route"] = classify_macos_target(source)
    try:
        from AppKit import NSWorkspace

        found = []
        for app in NSWorkspace.sharedWorkspace().runningApplications():
            target = {
                "pid": int(app.processIdentifier()),
                "name": str(app.localizedName() or ""),
                "bundle_id": str(app.bundleIdentifier() or ""),
            }
            target["route"] = classify_macos_target(target)
            if target["route"] in TARGET_ORDER:
                found.append(target)
        return choose_target_record(found, route, source) or {}
    except Exception:
        return {}


def _choose_chat_target(targets: list[dict], route: str | None = None) -> int | None:
    source = dict(getattr(core, "_ANNOTA_CAPTURE_SOURCE_TARGET", {}) or {})
    selected = choose_target_record(targets, route, source)
    hwnd = selected.get("hwnd") if selected else None
    return int(hwnd) if isinstance(hwnd, int) and hwnd else None


def _find_chat_window() -> int | None:
    return _choose_chat_target(core.detect_chat_targets(), core._SEND_ROUTE_OVERRIDE)


def _send_button_label(route: str | None = None) -> str:
    return target_label(route)


def _set_pending_send_route(route: str | None, send_button) -> None:
    selected_route = None if route in (None, "auto") else route
    core._PENDING_SEND_ROUTE = selected_route
    send_button.setText(target_label(selected_route))
    send_button.setToolTip(target_description(selected_route))
    send_button.setProperty("annotaSendRoute", selected_route or "auto")


def _add_send_route_menu(root, send_button=None):
    if root.property("annotaRouteMenuAdded"):
        return
    if send_button is None:
        buttons = root.findChildren(core.QPushButton)
        send_button = next(
            (
                button
                for button in buttons
                if button.objectName() in {"sendButton", "toolbarPrimary"}
                or button.text().strip() in {"Auto Send", "Send", "Copy for Manual Paste"}
            ),
            None,
        )
    if send_button is None:
        return

    _set_pending_send_route(core._PENDING_SEND_ROUTE, send_button)
    parent = send_button.parentWidget()
    layout = core._find_layout_containing(parent.layout() if parent else None, send_button)
    if layout is None:
        layout = core._find_layout_containing(root.layout(), send_button)
    if layout is None:
        return

    route_button = QToolButton(parent or root)
    route_button.setObjectName("sendRouteButton")
    route_button.setArrowType(core.Qt.DownArrow)
    route_button.setToolButtonStyle(core.Qt.ToolButtonIconOnly)
    route_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    route_button.setToolTip("Choose Auto Send or one supported destination")
    route_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    route_button.setFixedWidth(34)
    route_button.setFixedHeight(max(34, send_button.sizeHint().height()))

    menu = QMenu(route_button)
    auto_action = menu.addAction("Auto Send (Recommended)")
    auto_action.triggered.connect(
        lambda _checked=False, b=send_button: _set_pending_send_route(None, b)
    )
    menu.addSeparator()
    for route, label in SUPPORTED_TARGETS:
        action = menu.addAction(label)
        action.triggered.connect(
            lambda _checked=False, r=route, b=send_button: _set_pending_send_route(r, b)
        )
    menu.addSeparator()
    copy_action = menu.addAction("Copy for manual paste")
    copy_action.triggered.connect(
        lambda _checked=False, b=send_button: _set_pending_send_route("clipboard", b)
    )
    route_button.setMenu(menu)
    layout.insertWidget(layout.indexOf(send_button) + 1, route_button, 0, core.Qt.AlignVCenter)
    root.setProperty("annotaRouteMenuAdded", True)
    root._annota_route_button = route_button


def _skip_multi_review_enabled(overlay) -> bool:
    settings = getattr(overlay, "settings", None)
    if settings is None:
        return False
    return settings.value(SKIP_MULTI_REVIEW_KEY, False, type=bool)


def _send_overlay_without_review(overlay) -> None:
    if not overlay.annotations:
        return
    core._apply_pending_send_route()
    path, message, meta_path = overlay._build_payload()
    core._diagnostic_event(
        "payload_ready",
        image=path,
        metadata=meta_path,
        annotation_count=len(overlay.annotations),
        review_skipped=True,
    )
    overlay.finishedCapture.emit(path, message, meta_path)
    core._clear_pending_send_route()
    overlay.close()


def _auto_send_or_review(overlay) -> None:
    count = len(overlay.annotations)
    if count == 0:
        return
    if count == 1 or _skip_multi_review_enabled(overlay):
        _send_overlay_without_review(overlay)
    else:
        overlay._show_review()


def _save_and_auto_send(self, note: str) -> None:
    if not self._commit_pending_note(note):
        return
    self.toolbar.hide()
    _auto_send_or_review(self)


def _build_payload_clean_message(self):
    """Remove machine metadata from chat text and optionally append the AI instruction."""
    image_path, message, meta_path = _ORIGINAL_BUILD_PAYLOAD(self)
    hidden_prefixes = ("Application:", "Window:", "Display:", "DPI scale:", "Timestamp:")
    lines = []
    for line in message.splitlines():
        if line.startswith(hidden_prefixes):
            continue
        if line.strip() == AI_IMPLEMENTATION_INSTRUCTION:
            continue
        lines.append(line)
    while lines and not lines[-1].strip():
        lines.pop()
    if self.settings.value(INCLUDE_AI_INSTRUCTION_KEY, False, type=bool):
        lines.extend(["", AI_IMPLEMENTATION_INSTRUCTION])
    clean_message = "\n".join(lines)
    Path(image_path).with_suffix(".txt").write_text(clean_message, encoding="utf-8")
    return image_path, clean_message, meta_path


def _default_send_route(settings) -> str | None:
    route = str(settings.value(DEFAULT_SEND_ROUTE_KEY, "auto") or "auto")
    if route == "auto":
        return None
    if route == "clipboard" or route in TARGET_ORDER:
        return route
    return None


def _overlay_init_with_direct_auto_send(self, settings) -> None:
    _ORIGINAL_OVERLAY_INIT(self, settings)
    _set_pending_send_route(_default_send_route(settings), self.send_btn)
    with suppress(Exception):
        self.send_btn.clicked.disconnect()
    self.send_btn.clicked.connect(lambda: _auto_send_or_review(self))


def _settings_init_with_options(self, settings, parent=None) -> None:
    _ORIGINAL_SETTINGS_INIT(self, settings, parent)
    self.skip_review_multiple = QCheckBox(
        "Skip Review and Auto Send when multiple annotations are ready"
    )
    self.skip_review_multiple.setObjectName("skipReviewMultiple")
    self.skip_review_multiple.setChecked(settings.value(SKIP_MULTI_REVIEW_KEY, False, type=bool))
    self.skip_review_multiple.setToolTip(
        "When enabled, Auto Send immediately inserts two or more annotations without opening Review."
    )
    self.include_ai_instruction = QCheckBox(
        "Include AI implementation instruction with annotation notes"
    )
    self.include_ai_instruction.setObjectName("includeAiInstruction")
    self.include_ai_instruction.setChecked(
        settings.value(INCLUDE_AI_INSTRUCTION_KEY, False, type=bool)
    )
    self.include_ai_instruction.setToolTip(AI_IMPLEMENTATION_INSTRUCTION)
    self.default_send_route = QComboBox()
    self.default_send_route.setObjectName("defaultSendRoute")
    self.default_send_route.setToolTip(
        "Choose the destination Annota should use by default for each new annotation session."
    )
    self.default_send_route.addItem("Auto Send (Recommended)", "auto")
    for route, label in SUPPORTED_TARGETS:
        self.default_send_route.addItem(label, route)
    self.default_send_route.addItem("Copy for manual paste", "clipboard")
    saved_route = str(settings.value(DEFAULT_SEND_ROUTE_KEY, "auto") or "auto")
    saved_index = self.default_send_route.findData(saved_route)
    self.default_send_route.setCurrentIndex(saved_index if saved_index >= 0 else 0)

    behavior_parent = self.start_login.parentWidget()
    if behavior_parent is not None and behavior_parent.layout() is not None:
        layout = behavior_parent.layout()
        clear_index = layout.indexOf(self.clear_after)
        route_row = core.QHBoxLayout()
        route_row.addWidget(core.QLabel("Default Send destination"))
        route_row.addStretch(1)
        route_row.addWidget(self.default_send_route)
        route_index = clear_index if clear_index >= 0 else layout.count()
        layout.insertLayout(route_index, route_row)
        insert_at = layout.indexOf(self.clear_after) + 1
        layout.insertWidget(insert_at, self.skip_review_multiple)
        layout.insertWidget(insert_at + 1, self.include_ai_instruction)


def _settings_save_with_options(self) -> None:
    _ORIGINAL_SETTINGS_SAVE(self)
    if self.result() == QDialog.DialogCode.Accepted:
        self.settings.setValue(SKIP_MULTI_REVIEW_KEY, self.skip_review_multiple.isChecked())
        self.settings.setValue(
            INCLUDE_AI_INSTRUCTION_KEY,
            self.include_ai_instruction.isChecked(),
        )
        self.settings.setValue(
            DEFAULT_SEND_ROUTE_KEY,
            self.default_send_route.currentData() or "auto",
        )


def _install_routing_extension() -> None:
    core._ANNOTA_CAPTURE_SOURCE_TARGET = {}
    core.ROUTE_PRIORITY = TARGET_ORDER
    core.classify_chat_window = classify_windows_target
    core.classify_macos_app = _classify_macos_app
    core.choose_chat_target = _choose_chat_target
    core.find_chat_window = _find_chat_window
    core.macos_find_chat_target = _macos_find_chat_target
    core.active_window_context = _active_window_context
    core._send_button_label = _send_button_label
    core._set_pending_send_route = _set_pending_send_route
    core._add_send_route_menu = _add_send_route_menu
    core._annota_auto_send_or_review = _auto_send_or_review
    core._annota_skip_multi_review_key = SKIP_MULTI_REVIEW_KEY
    core._annota_include_ai_instruction_key = INCLUDE_AI_INSTRUCTION_KEY
    core._annota_ai_implementation_instruction = AI_IMPLEMENTATION_INSTRUCTION
    core._annota_default_send_route_key = DEFAULT_SEND_ROUTE_KEY
    core._default_send_route = _default_send_route
    core.AnnotaApp.activate_annotation = _activate_annotation_with_source
    core.AnnotationOverlay.__init__ = _overlay_init_with_direct_auto_send
    core.AnnotationOverlay._save_and_review = _save_and_auto_send
    core.AnnotationOverlay._build_payload = _build_payload_clean_message
    core.SettingsDialog.__init__ = _settings_init_with_options
    core.SettingsDialog._save = _settings_save_with_options


_install_routing_extension()

if __name__ != "__main__":
    sys.modules[__name__] = core
else:
    raise SystemExit(core.main())
