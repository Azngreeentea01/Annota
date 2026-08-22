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

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QMenu,
    QPushButton,
    QSizePolicy,
    QToolButton,
)

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
_ORIGINAL_NOTECARD_INIT = core.NoteCard.__init__
_ORIGINAL_REVIEWCARD_INIT = core.ReviewCard.__init__
_ORIGINAL_COMMIT_PENDING_NOTE = core.AnnotationOverlay._commit_pending_note
_ORIGINAL_PAINT_EVENT = core.AnnotationOverlay.paintEvent
_ORIGINAL_REVIEW_PREVIEW = core.AnnotationOverlay._make_review_preview
_ORIGINAL_SHOW_NOTE_CARD = core.AnnotationOverlay._show_note_card
_ORIGINAL_OVERLAY_SEND = core.AnnotationOverlay._send
SKIP_MULTI_REVIEW_KEY = "behavior/skip_review_multiple"
INCLUDE_AI_INSTRUCTION_KEY = "behavior/include_ai_instruction"
DEFAULT_SEND_ROUTE_KEY = "behavior/default_send_route"
TARGET_ICON_DIR = core.ASSET_DIR / "targets"
CANCEL_ICON_PATH = core.ASSET_DIR / "cancel.svg"
NEW_ANNOTATION_ICON_PATH = core.ASSET_DIR / "new_annotation.svg"
MANUAL_PASTE_ICON_PATH = core.ASSET_DIR / "manual_paste.svg"

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
    """Capture the source before overlay focus, or resume a paused session."""
    if (
        self.overlay
        and not self.overlay.isVisible()
        and self.overlay.annotations
        and not getattr(self.overlay, "_annota_session_completed", False)
    ):
        _resume_annotation_session(self.overlay)
        return
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


def _target_icon(route: str) -> QIcon:
    path = TARGET_ICON_DIR / f"{route}.svg"
    return QIcon(str(path)) if path.exists() else QIcon()


def _style_approved_note_card(card, send_button) -> None:
    """Match the approved wide Note Card proportions without clipping at high DPI."""
    card.setFixedWidth(820)
    if card.layout() is not None:
        card.layout().setContentsMargins(24, 22, 24, 22)
        card.layout().setSpacing(14)

    editor = getattr(card, "editor", None)
    if editor is not None:
        editor.setFixedHeight(110)

    buttons = {button.text().strip(): button for button in card.findChildren(core.QPushButton)}
    cancel = buttons.get("Cancel")
    new_annotation = buttons.get("+ New Annotation")
    if cancel is not None:
        cancel.setText("Cancel")
        cancel.setFixedSize(112, 48)
        if CANCEL_ICON_PATH.exists():
            cancel.setIcon(QIcon(str(CANCEL_ICON_PATH)))
            cancel.setIconSize(QSize(21, 21))
    if new_annotation is not None:
        new_annotation.setText("New Annotation")
        new_annotation.setFixedSize(178, 48)
        if NEW_ANNOTATION_ICON_PATH.exists():
            new_annotation.setIcon(QIcon(str(NEW_ANNOTATION_ICON_PATH)))
            new_annotation.setIconSize(QSize(22, 22))

    send_button.setFixedSize(158, 48)
    send_button.setIconSize(QSize(22, 22))
    route_button = getattr(card, "_annota_route_button", None)
    if route_button is not None:
        route_button.setFixedSize(46, 48)

    manual = getattr(card, "_annota_manual_paste_button", None)
    if manual is not None:
        manual.setFixedSize(150, 48)
        manual.setObjectName("manualPasteButton")
        if MANUAL_PASTE_ICON_PATH.exists():
            manual.setIcon(QIcon(str(MANUAL_PASTE_ICON_PATH)))
            manual.setIconSize(QSize(21, 21))

    row = core._find_layout_containing(card.layout(), send_button)
    if row is not None:
        # The old 430px card used a stretch spacer; remove it so the approved
        # five-control row remains evenly aligned instead of crushing labels.
        for index in range(row.count() - 1, -1, -1):
            item = row.itemAt(index)
            if item.spacerItem() is not None:
                row.takeAt(index)
        row.setSpacing(12)
        row.setAlignment(core.Qt.AlignHCenter | core.Qt.AlignVCenter)


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
    menu.setObjectName("sendRouteMenu")
    menu.setMinimumWidth(286)
    header = menu.addAction("Send to")
    header.setEnabled(False)
    menu.addSeparator()
    auto_action = menu.addAction(QIcon(str(core.SEND_ICON_PATH)), "Auto Send")
    auto_action.triggered.connect(
        lambda _checked=False, b=send_button: _set_pending_send_route(None, b)
    )
    menu.addSeparator()
    primary_routes = ("chatgpt", "codex", "claude", "cursor", "vscode", "windsurf", "opencode")
    secondary_routes = ("cline", "roo_code", "github_copilot", "gemini")
    labels = dict(SUPPORTED_TARGETS)
    for route in primary_routes:
        action = menu.addAction(_target_icon(route), labels[route])
        action.triggered.connect(
            lambda _checked=False, r=route, b=send_button: _set_pending_send_route(r, b)
        )
    menu.addSeparator()
    for route in secondary_routes:
        action = menu.addAction(_target_icon(route), labels[route])
        action.triggered.connect(
            lambda _checked=False, r=route, b=send_button: _set_pending_send_route(r, b)
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


def _reset_completed_session(overlay) -> None:
    """Discard all capture state after Send or Manual Paste completes."""
    overlay._annota_session_completed = True
    overlay.annotations.clear()
    getattr(overlay, "_annota_annotation_frames", []).clear()
    overlay.pending_rect = None
    overlay.current_rect = None
    overlay.drag_start = None
    overlay.interaction = None
    overlay.interaction_start = None
    overlay.interaction_rect = None
    note_card = getattr(overlay, "note_card", None)
    if note_card:
        note_card.close()
        overlay.note_card = None
    review_card = getattr(overlay, "review_card", None)
    if review_card:
        review_card.close()
        overlay.review_card = None
    toolbar = getattr(overlay, "toolbar", None)
    if toolbar is not None:
        toolbar.hide()
    core._ANNOTA_CAPTURE_SOURCE_TARGET = {}
    core._diagnostic_event("annotation_session_completed")


def _send_overlay_without_review(overlay, force_route: str | None = None) -> None:
    if not overlay.annotations:
        return
    if force_route is None:
        core._apply_pending_send_route()
    else:
        core._SEND_ROUTE_OVERRIDE = force_route
    path, message, meta_path = overlay._build_payload()
    core._diagnostic_event(
        "payload_ready",
        image=path,
        metadata=meta_path,
        annotation_count=len(overlay.annotations),
        review_skipped=True,
    )
    overlay.finishedCapture.emit(path, message, meta_path)
    _reset_completed_session(overlay)
    core._clear_pending_send_route()
    overlay.close()


def _send_review_and_reset(self) -> None:
    """Keep Review behavior, then clear the completed session after a real send."""
    sending = bool(self.annotations and self.review_card and self.review_card.isVisible())
    _ORIGINAL_OVERLAY_SEND(self)
    if sending:
        _reset_completed_session(self)


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
    composite = _render_session_composite(self)
    if composite is not None:
        composite.save(image_path, "PNG")
    Path(image_path).with_suffix(".txt").write_text(clean_message, encoding="utf-8")
    return image_path, clean_message, meta_path


def _default_send_route(settings) -> str | None:
    route = str(settings.value(DEFAULT_SEND_ROUTE_KEY, "auto") or "auto")
    if route == "auto":
        return None
    if route in TARGET_ORDER:
        return route
    return None


def _note_card_init_with_manual_paste(self, number: int, parent=None) -> None:
    _ORIGINAL_NOTECARD_INIT(self, number, parent)
    send_button = next(
        (b for b in self.findChildren(core.QPushButton) if b.objectName() == "sendButton"), None
    )
    if send_button is not None:

        def manual_from_note():
            note = self._note_text()
            if note:
                self.manualPasteRequested.emit(note)

        _add_manual_paste_button(self, send_button, manual_from_note)
        _style_approved_note_card(self, send_button)


def _save_and_manual_paste(self, note: str) -> None:
    """Commit the current note and finish the session immediately via clipboard."""
    if not self._commit_pending_note(note):
        return
    core._PENDING_SEND_ROUTE = "clipboard"
    self.toolbar.hide()
    _send_overlay_without_review(self, force_route="clipboard")


def _show_note_card_with_manual_paste(self) -> None:
    _ORIGINAL_SHOW_NOTE_CARD(self)
    if self.note_card is not None:
        with suppress(Exception):
            self.note_card.manualPasteRequested.connect(
                lambda note: _save_and_manual_paste(self, note)
            )


def _review_card_init_with_manual_paste(self, annotations, preview, parent=None) -> None:
    _ORIGINAL_REVIEWCARD_INIT(self, annotations, preview, parent)
    send_button = next(
        (b for b in self.findChildren(core.QPushButton) if b.objectName() == "sendButton"), None
    )
    if send_button is not None:

        def manual_from_review():
            core._PENDING_SEND_ROUTE = "clipboard"
            self._request_send()

        _add_manual_paste_button(self, send_button, manual_from_review)


def _commit_pending_note_with_frame(self, note: str) -> bool:
    if not self.pending_rect:
        return False
    frame = {
        "frame_id": getattr(self, "_annota_current_frame_id", 0),
        "snapshot": self.snapshot.copy(),
        "rect": core.QRect(self.pending_rect),
        "dpr": float(self.dpr),
        "screen_geometry": core.QRect(self.screen_geometry),
    }
    committed = _ORIGINAL_COMMIT_PENDING_NOTE(self, note)
    if committed:
        self._annota_annotation_frames.append(frame)
        self.update()
    return committed


def _paint_event_current_frame(self, event) -> None:
    frames = getattr(self, "_annota_annotation_frames", [])
    if not frames or not self.annotations:
        _ORIGINAL_PAINT_EVENT(self, event)
        return
    current_id = getattr(self, "_annota_current_frame_id", 0)
    original_annotations = self.annotations
    self.annotations = [
        ann
        for ann, frame in zip(original_annotations, frames, strict=True)
        if frame.get("frame_id") == current_id
    ]
    try:
        _ORIGINAL_PAINT_EVENT(self, event)
    finally:
        self.annotations = original_annotations


def _render_session_composite(self) -> core.QPixmap | None:
    frames = getattr(self, "_annota_annotation_frames", [])
    if not frames or len(frames) != len(self.annotations):
        return None
    padding_pct = int(self.settings.value("behavior/context_padding", 15))
    rendered = []
    max_width = 1
    total_height = 0
    gap = 18
    for ann, frame in zip(self.annotations, frames, strict=True):
        rect = core.QRect(frame["rect"])
        dpr = float(frame["dpr"] or 1.0)
        snapshot = frame["snapshot"]
        logical_bounds = core.QRect(
            0, 0, round(snapshot.width() / dpr), round(snapshot.height() / dpr)
        )
        pad_x = max(24, int(rect.width() * padding_pct / 100))
        pad_y = max(24, int(rect.height() * padding_pct / 100))
        crop = rect.adjusted(-pad_x, -pad_y, pad_x, pad_y).intersected(logical_bounds)
        device_crop = core.QRect(
            round(crop.x() * dpr),
            round(crop.y() * dpr),
            max(1, round(crop.width() * dpr)),
            max(1, round(crop.height() * dpr)),
        )
        piece = snapshot.copy(device_crop)
        painter = core.QPainter(piece)
        local = rect.translated(-crop.topLeft())
        draw_rect = core.QRect(
            round(local.x() * dpr),
            round(local.y() * dpr),
            max(1, round(local.width() * dpr)),
            max(1, round(local.height() * dpr)),
        )
        painter.setPen(core.QPen(core.QColor(core.LAVENDER_DARK), max(3, round(4 * dpr))))
        painter.setBrush(core.Qt.NoBrush)
        painter.drawRoundedRect(draw_rect, round(6 * dpr), round(6 * dpr))
        marker_size = max(26, round(27 * dpr))
        marker = core.QRect(
            draw_rect.left() - marker_size // 2,
            draw_rect.top() - marker_size // 2,
            marker_size,
            marker_size,
        )
        painter.setBrush(core.QColor(core.LAVENDER_DARK))
        painter.setPen(core.Qt.NoPen)
        painter.drawEllipse(marker)
        painter.setPen(core.QColor("white"))
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(max(12, round(13 * dpr)))
        painter.setFont(font)
        painter.drawText(marker, core.Qt.AlignCenter, str(ann.index))
        painter.end()
        rendered.append(piece)
        max_width = max(max_width, piece.width())
        total_height += piece.height()
    total_height += gap * max(0, len(rendered) - 1)
    canvas = core.QPixmap(max_width, total_height)
    canvas.fill(core.QColor("white"))
    painter = core.QPainter(canvas)
    y = 0
    for piece in rendered:
        painter.drawPixmap((max_width - piece.width()) // 2, y, piece)
        y += piece.height() + gap
    painter.end()
    return canvas


def _make_review_preview_session(self):
    return _render_session_composite(self) or _ORIGINAL_REVIEW_PREVIEW(self)


def _overlay_init_with_direct_auto_send(self, settings) -> None:
    _ORIGINAL_OVERLAY_INIT(self, settings)
    self._annota_annotation_frames = []
    self._annota_current_frame_id = 0
    self._annota_session_completed = False
    _set_pending_send_route(_default_send_route(settings), self.send_btn)
    with suppress(Exception):
        self.send_btn.clicked.disconnect()
    self.send_btn.clicked.connect(lambda: _auto_send_or_review(self))
    _add_manual_paste_button(self, self.send_btn, lambda: _manual_paste_overlay(self))


def _manual_paste_overlay(overlay) -> None:
    if not overlay.annotations:
        return
    core._PENDING_SEND_ROUTE = "clipboard"
    _send_overlay_without_review(overlay, force_route="clipboard")


def _add_manual_paste_button(root, send_button, callback) -> QPushButton | None:
    parent = send_button.parentWidget()
    layout = core._find_layout_containing(parent.layout() if parent else None, send_button)
    if layout is None:
        layout = core._find_layout_containing(root.layout(), send_button)
    if layout is None:
        return None
    button = QPushButton("Manual Paste", parent or root)
    button.setObjectName("manualPasteButton")
    if MANUAL_PASTE_ICON_PATH.exists():
        button.setIcon(QIcon(str(MANUAL_PASTE_ICON_PATH)))
        button.setIconSize(QSize(21, 21))
    button.setToolTip("Copy the annotation image and notes for you to paste manually.")
    button.clicked.connect(callback)
    route_button = getattr(root, "_annota_route_button", None)
    anchor = (
        route_button
        if route_button is not None and layout.indexOf(route_button) >= 0
        else send_button
    )
    layout.insertWidget(layout.indexOf(anchor) + 1, button, 0, core.Qt.AlignVCenter)
    root._annota_manual_paste_button = button
    return button


def _pause_annotation_session(self) -> None:
    """Hide the overlay while preserving the current annotation session."""
    if self.note_card and self.pending_rect:
        note = self.note_card.editor.toPlainText().strip()
        if note:
            self._commit_pending_note(note)
    if self.review_card:
        self.review_card.hide()
    if self.note_card:
        self.note_card.hide()
    self.toolbar.hide()
    self.hide()
    self.mode = "select"
    self.setCursor(core.Qt.CrossCursor)
    core._diagnostic_event("annotation_session_paused", annotation_count=len(self.annotations))


def _resume_annotation_session(self) -> None:
    """Refresh the desktop snapshot and resume a paused annotation session."""
    self.screen = (
        core.QGuiApplication.screenAt(core.QCursor.pos()) or core.QGuiApplication.primaryScreen()
    )
    self.snapshot = self.screen.grabWindow(0)
    self.screen_geometry = self.screen.geometry()
    self.dpr = float(self.screen.devicePixelRatio() or 1.0)
    self.setGeometry(self.screen_geometry)
    self._annota_current_frame_id = getattr(self, "_annota_current_frame_id", 0) + 1
    self.pending_rect = None
    self.current_rect = None
    self.mode = "select"
    self.setCursor(core.Qt.CrossCursor)
    self.show()
    self.raise_()
    self.activateWindow()
    core._diagnostic_event("annotation_session_resumed", annotation_count=len(self.annotations))


def _overlay_keypress_with_pause(self, event) -> None:
    if event.key() == core.Qt.Key_Escape:
        _pause_annotation_session(self)
        event.accept()
        return
    core.AnnotationOverlay._annota_original_keypress(self, event)


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
    core._reset_completed_session = _reset_completed_session
    core._send_overlay_without_review = _send_overlay_without_review
    core.AnnotaApp.activate_annotation = _activate_annotation_with_source
    if not hasattr(core.AnnotationOverlay, "_annota_original_keypress"):
        core.AnnotationOverlay._annota_original_keypress = core.AnnotationOverlay.keyPressEvent
    core.NoteCard.__init__ = _note_card_init_with_manual_paste
    core.ReviewCard.__init__ = _review_card_init_with_manual_paste
    core.AnnotationOverlay.__init__ = _overlay_init_with_direct_auto_send
    core.AnnotationOverlay._show_note_card = _show_note_card_with_manual_paste
    core.AnnotationOverlay._commit_pending_note = _commit_pending_note_with_frame
    core.AnnotationOverlay.paintEvent = _paint_event_current_frame
    core.AnnotationOverlay._make_review_preview = _make_review_preview_session
    core.AnnotationOverlay.keyPressEvent = _overlay_keypress_with_pause
    core.AnnotationOverlay._save_and_review = _save_and_auto_send
    core.AnnotationOverlay._build_payload = _build_payload_clean_message
    core.AnnotationOverlay._send = _send_review_and_reset
    core.SettingsDialog.__init__ = _settings_init_with_options
    core.SettingsDialog._save = _settings_save_with_options


_install_routing_extension()

if __name__ != "__main__":
    sys.modules[__name__] = core
else:
    raise SystemExit(core.main())
