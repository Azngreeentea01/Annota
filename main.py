"""Annota application entry point with supported-app Auto Send integration.

The established application stays in ``annota_core``. This module installs the
small routing extension before starting it, keeping target detection isolated
and testable without disturbing the annotation workflow.
"""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QMenu, QSizePolicy, QToolButton

import annota_core as core
from target_routing import (
    SUPPORTED_TARGETS,
    TARGET_ORDER,
    choose_target_record,
    classify_macos_target,
    classify_windows_target,
    target_label,
)

_ORIGINAL_PASTE_SHORTCUT = core.paste_shortcut
_ORIGINAL_SEND_TO_CURRENT_CHAT = core.AnnotaApp._send_to_current_chat
_ORIGINAL_OVERLAY_INIT = core.AnnotationOverlay.__init__
_SEND_SESSION = {"active": False, "paste_count": 0, "controller": None}


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


def _active_window_context() -> tuple[str, str]:
    if core.is_macos():
        target = core.macos_frontmost_app()
        target["route"] = classify_macos_target(target)
        core._ANNOTA_CAPTURE_SOURCE_TARGET = target
        return target.get("name", "macOS"), "Active macOS app"
    if os.name != "nt":
        core._ANNOTA_CAPTURE_SOURCE_TARGET = {}
        return core.platform.system(), "Active desktop window"
    target = _windows_frontmost_target()
    core._ANNOTA_CAPTURE_SOURCE_TARGET = target
    executable = str(target.get("executable", ""))
    process_name = Path(executable).name if executable else f"PID {target.get('pid', 0)}"
    return process_name, target.get("title", "Unknown window")


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


def _set_pending_send_route(route: str | None, send_button):
    core._PENDING_SEND_ROUTE = None if route in (None, "auto") else route
    send_button.setText(target_label(core._PENDING_SEND_ROUTE))
    if core._PENDING_SEND_ROUTE is None:
        names = ", ".join(label for _route, label in SUPPORTED_TARGETS)
        send_button.setToolTip(
            f"Auto Send: return to the supported app active at capture time first; otherwise try {names}; clipboard fallback is always safe."
        )
    else:
        send_button.setToolTip(f"Use {target_label(core._PENDING_SEND_ROUTE)} after Review")


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
                or button.text().strip().startswith(("Auto Send", "Send to "))
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


def _submit_shortcut() -> tuple[bool, str]:
    """Submit the populated composer after both payload paste operations succeed."""
    if core.is_macos():
        try:
            import Quartz

            enter_key_code = 36
            key_down = Quartz.CGEventCreateKeyboardEvent(None, enter_key_code, True)
            key_up = Quartz.CGEventCreateKeyboardEvent(None, enter_key_code, False)
            if key_down is None or key_up is None:
                return False, "macOS could not create a Return key event"
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, key_down)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, key_up)
            return True, ""
        except Exception as exc:
            return False, f"macOS submit event failed: {exc}"

    if core.keyboard is None:
        return False, "Keyboard backend unavailable"
    try:
        controller = core.keyboard.Controller()
        controller.press(core.keyboard.Key.enter)
        controller.release(core.keyboard.Key.enter)
        return True, ""
    except Exception as exc:
        return False, f"Submit shortcut failed: {exc}"


def _finish_auto_send() -> None:
    if not _SEND_SESSION["active"] or _SEND_SESSION["paste_count"] < 2:
        return
    controller = _SEND_SESSION.get("controller")
    _SEND_SESSION["active"] = False
    ok, error = _submit_shortcut()
    if controller is None:
        return
    if ok:
        controller._show_toast(
            "Annotation sent",
            "Annota inserted the screenshot and notes, then submitted them to the selected chat.",
            4200,
        )
    else:
        controller._show_toast(
            "Ready, but not submitted",
            f"The screenshot and notes were inserted, but Annota could not press Send: {error}. Press Enter/Return to send them.",
            6500,
        )


def _paste_shortcut_with_auto_submit() -> tuple[bool, str]:
    ok, error = _ORIGINAL_PASTE_SHORTCUT()
    if ok and _SEND_SESSION["active"]:
        _SEND_SESSION["paste_count"] += 1
        if _SEND_SESSION["paste_count"] == 2:
            core.QTimer.singleShot(220, _finish_auto_send)
    return ok, error


def _send_to_current_chat_with_auto_submit(self, image_path: str, message: str):
    _SEND_SESSION.update(active=True, paste_count=0, controller=self)
    _ORIGINAL_SEND_TO_CURRENT_CHAT(self, image_path, message)
    # A failed/fallback send never reaches two successful paste operations.
    core.QTimer.singleShot(10000, lambda: _SEND_SESSION.update(active=False))


def _send_overlay_without_review(overlay) -> None:
    """Finish a one-annotation Auto Send without opening the Review card."""
    if len(overlay.annotations) != 1:
        overlay._show_review()
        return
    core._apply_pending_send_route()
    path, message, meta_path = overlay._build_payload()
    core._diagnostic_event(
        "payload_ready",
        image=path,
        metadata=meta_path,
        annotation_count=1,
        review_skipped=True,
    )
    overlay.finishedCapture.emit(path, message, meta_path)
    core._clear_pending_send_route()
    overlay.close()


def _auto_send_or_review(overlay) -> None:
    """Skip Review only for a single annotation; review multi-annotation sends."""
    if len(overlay.annotations) == 1:
        _send_overlay_without_review(overlay)
    elif len(overlay.annotations) > 1:
        overlay._show_review()


def _save_and_auto_send(self, note: str) -> None:
    if not self._commit_pending_note(note):
        return
    self.toolbar.hide()
    _auto_send_or_review(self)


def _overlay_init_with_direct_auto_send(self, settings) -> None:
    _ORIGINAL_OVERLAY_INIT(self, settings)
    # Review remains an explicit preview action. Auto Send follows the
    # one-annotation fast path and only previews when multiple annotations exist.
    with suppress(Exception):
        self.send_btn.clicked.disconnect()
    self.send_btn.clicked.connect(lambda: _auto_send_or_review(self))


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
    core._annota_submit_shortcut = _submit_shortcut
    core._annota_auto_send_or_review = _auto_send_or_review
    core.paste_shortcut = _paste_shortcut_with_auto_submit
    core.AnnotaApp._send_to_current_chat = _send_to_current_chat_with_auto_submit
    core.AnnotationOverlay.__init__ = _overlay_init_with_direct_auto_send
    core.AnnotationOverlay._save_and_review = _save_and_auto_send


# ``suppress`` is imported late above only for the signal reconnect wrapper.
from contextlib import suppress

_install_routing_extension()

# When imported by tests or tooling, expose the patched core module directly so
# monkeypatching and private route-state assertions continue to work normally.
if __name__ != "__main__":
    sys.modules[__name__] = core
else:
    raise SystemExit(core.main())
