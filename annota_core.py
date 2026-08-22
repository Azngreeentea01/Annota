"""Annota - local-first desktop annotation utility for Windows and macOS.

The module contains the small Qt desktop application, platform integration,
annotation workflow, payload generation, and safe Codex/ChatGPT routing.
"""

from __future__ import annotations

import ctypes
import json
import os
import platform
import plistlib
import queue
import socket
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable
from contextlib import suppress
from ctypes import wintypes
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import (
    QMimeData,
    QObject,
    QPoint,
    QRect,
    QSettings,
    Qt,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QCursor,
    QDesktopServices,
    QGuiApplication,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSystemTrayIcon,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

try:
    from pynput import keyboard
except Exception:  # pragma: no cover
    keyboard = None

try:
    import winreg
except ImportError:  # pragma: no cover
    winreg = None

APP_NAME = "Annota"
ORG_NAME = "SoftWify"
APP_VERSION = "0.2.5"
LAVENDER = "#B9A7FF"
LAVENDER_DARK = "#8E68F4"
MIN_SELECTION = 18
HANDLE_RADIUS = 9
INSTANCE_HOST = "127.0.0.1"
INSTANCE_PORT = 47643
QUICK_ANNOTATE_FLAGS = {"--annotate", "--quick-annotate"}
SHELL_VERB_NAME = "SoftWify.Annota.Annotate"


def _runtime_root() -> Path:
    bundled = getattr(sys, "_MEIPASS", None)
    return Path(bundled) if bundled else Path(__file__).resolve().parent


ASSET_DIR = _runtime_root() / "assets"
ICON_PATH = ASSET_DIR / "annota.svg"
SEND_ICON_PATH = ASSET_DIR / "send.svg"
HOTKEY_HELPER_PATH = _runtime_root() / "annota_hotkey"

DIAGNOSTIC_FILE_ENV = "ANNOTA_DIAGNOSTIC_FILE"


def _diagnostic_event(event: str, **fields) -> None:
    """Append a local JSONL runtime event when diagnostics are explicitly enabled."""
    target = os.environ.get(DIAGNOSTIC_FILE_ENV, "").strip()
    if not target:
        return
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        "event": event,
        **fields,
    }
    try:
        output = Path(target)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError:
        return


def _widget_diagnostic_controls(widget: QWidget) -> dict[str, list[int]]:
    """Return overlay-relative geometry for visible buttons in a diagnostic event."""
    controls: dict[str, list[int]] = {}
    origin = widget.mapTo(widget.window(), QPoint(0, 0))
    children = [*widget.findChildren(QPushButton), *widget.findChildren(QToolButton)]
    for child in children:
        if not child.isVisible():
            continue
        label = child.text().strip() or child.objectName()
        pos = child.mapTo(widget.window(), QPoint(0, 0))
        controls[label] = [pos.x(), pos.y(), child.width(), child.height()]
    controls["__widget__"] = [origin.x(), origin.y(), widget.width(), widget.height()]
    return controls


APP_STYLE = r"""
QWidget { font-family: '.AppleSystemUIFont', 'SF Pro Text', 'Segoe UI Variable Text', 'Segoe UI', sans-serif; font-size: 10.5pt; color: #1D1930; }
#modePill { background: #7650E8; color: #FFFFFF; border: 1px solid rgba(255,255,255,70); border-radius: 15px; padding: 11px 18px; font-size: 10.5pt; font-weight: 700; }
#noteCard, #reviewCard, #statusToast { background: rgba(255,255,255,252); border: 2px solid #A990FA; border-radius: 16px; }
#reviewCard { background: #FDFCFF; }
#noteTitle { color: #1D1930; font-weight: 750; font-size: 12pt; }
#noteMarker, #toastBadge { background: #7650E8; color: #FFFFFF; border-radius: 14px; font-weight: 800; }
#reviewTitle { font-size: 18pt; font-weight: 800; color: #1D1930; }
#hint, #muted, #toastDetail { color: #5D576E; font-size: 9.5pt; }
#toastTitle { color: #1D1930; font-weight: 750; font-size: 11pt; }
#previewCard, #notesCard, #settingsCard { background: #FFFFFF; border: 1px solid #D8CFF0; border-radius: 12px; }
#previewImage { background: #F5F1FF; border-radius: 8px; padding: 4px; }
QTextEdit, QLineEdit, QSpinBox { background: #FFFFFF; color: #1D1930; border: 1px solid #CFC5EC; border-radius: 9px; padding: 8px; font-size: 10.5pt; selection-background-color: #C7B7FF; selection-color: #1D1930; }
QTextEdit:focus, QLineEdit:focus, QSpinBox:focus { border: 2px solid #7650E8; }
#primaryButton, #sendButton, #toolbarPrimary { background: #7650E8; color: #FFFFFF; border: none; border-radius: 9px; padding: 9px 15px; font-size: 10.5pt; font-weight: 700; }
#primaryButton:hover, #sendButton:hover, #toolbarPrimary:hover { background: #6741DB; }
#primaryButton:pressed, #sendButton:pressed, #toolbarPrimary:pressed { background: #5934C7; }
#secondaryButton, #toolbarButton, #iconButton { background: #FFFFFF; color: #1D1930; border: 1px solid #D5CDEE; border-radius: 9px; padding: 8px 13px; font-size: 10.25pt; font-weight: 650; }
#secondaryButton:hover, #toolbarButton:hover, #iconButton:hover { background: #EEE9FF; }
#toolbar { background: rgba(28,23,47,248); border: 1px solid rgba(255,255,255,48); border-radius: 13px; }
#toolbarButton { background: transparent; color: #FFFFFF; border: none; font-weight: 700; }
#toolbarButton:hover { background: rgba(255,255,255,24); }
#sendRouteButton { background: #7650E8; color: #FFFFFF; border: none; border-radius: 9px; padding: 7px 6px; min-width: 28px; max-width: 32px; font-weight: 800; }
#sendRouteButton:hover { background: #6741DB; }
#sendRouteButton:pressed { background: #5934C7; }
#reviewList { background: #FBFAFF; color: #1D1930; border: 1px solid #DDD6F2; border-radius: 9px; padding: 5px; outline: none; font-size: 10.25pt; }
#reviewList::item { padding: 10px 8px; border-bottom: 1px solid #E9E4F5; }
#reviewList::item:selected { background: #E9E1FF; color: #1D1930; border-radius: 7px; }
#dialogTitle { font-size: 22pt; font-weight: 800; color: #1D1930; }
#sectionTitle { font-size: 11.5pt; font-weight: 750; color: #6844D9; margin-top: 2px; }
QDialog { background: #FDFCFF; }
QCheckBox { spacing: 8px; font-size: 10.25pt; }
QMenu { background: #FFFFFF; color: #1D1930; border: 1px solid #D8CFF0; padding: 6px; font-size: 10.25pt; }
QMenu::item { padding: 8px 28px 8px 11px; border-radius: 6px; }
QMenu::item:selected { background: #EEE9FF; color: #1D1930; }
"""


@dataclass
class Annotation:
    index: int
    rect: tuple[int, int, int, int]
    note: str


class HotkeyBridge(QObject):
    activated = Signal()


class SubmitTextEdit(QTextEdit):
    submitted = Signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (
            event.modifiers() & Qt.ShiftModifier
        ):
            event.accept()
            self.submitted.emit()
            return
        super().keyPressEvent(event)


class StatusToast(QFrame):
    def __init__(self, title: str, detail: str, kind=None):
        super().__init__(None)
        self.setObjectName("statusToast")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedWidth(430)
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(12)
        badge = QLabel("A")
        badge.setObjectName("toastBadge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(34, 34)
        root.addWidget(badge)
        text = QVBoxLayout()
        text.setSpacing(3)
        heading = QLabel(title)
        heading.setObjectName("toastTitle")
        body = QLabel(detail)
        body.setObjectName("toastDetail")
        body.setWordWrap(True)
        text.addWidget(heading)
        text.addWidget(body)
        root.addLayout(text, 1)
        self.setStyleSheet(APP_STYLE)
        self.adjustSize()

    def show_for(self, milliseconds: int = 4200):
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        available = screen.availableGeometry()
        self.adjustSize()
        self.move(available.right() - self.width() - 22, available.bottom() - self.height() - 22)
        self.show()
        self.raise_()
        QTimer.singleShot(milliseconds, self.close)


class NoteCard(QFrame):
    newAnnotationRequested = Signal(str)
    reviewRequested = Signal(str)
    cancelRequested = Signal()

    def __init__(self, number: int, parent=None):
        super().__init__(parent)
        self.setObjectName("noteCard")
        self.setFixedWidth(430)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        title_row = QHBoxLayout()
        marker = QLabel(str(number))
        marker.setObjectName("noteMarker")
        marker.setAlignment(Qt.AlignCenter)
        marker.setFixedSize(28, 28)
        title = QLabel("What should change?")
        title.setObjectName("noteTitle")
        title_row.addWidget(marker)
        title_row.addWidget(title)
        title_row.addStretch(1)
        layout.addLayout(title_row)

        self.editor = SubmitTextEdit()
        self.editor.setPlaceholderText("Describe the change...")
        self.editor.setFixedHeight(96)
        self.editor.submitted.connect(self._new_annotation)
        layout.addWidget(self.editor)

        hint = QLabel(
            "Drag the selection to move it. Drag a corner to resize.\n"
            "Enter starts a new annotation; Shift+Enter adds a new line."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        row = QHBoxLayout()
        row.setSpacing(8)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        new_annotation = QPushButton("+ New Annotation")
        new_annotation.setObjectName("secondaryButton")
        auto_send = QPushButton("Auto Send")
        auto_send.setObjectName("sendButton")
        if SEND_ICON_PATH.exists():
            auto_send.setIcon(QIcon(str(SEND_ICON_PATH)))
        cancel.clicked.connect(self.cancelRequested)
        new_annotation.clicked.connect(self._new_annotation)
        auto_send.clicked.connect(self._review)
        row.addWidget(cancel)
        row.addStretch(1)
        row.addWidget(new_annotation)
        row.addWidget(auto_send)
        layout.addLayout(row)
        _add_send_route_menu(self, auto_send)

    def _note_text(self) -> str:
        return self.editor.toPlainText().strip()

    def _new_annotation(self):
        text = self._note_text()
        if text:
            self.newAnnotationRequested.emit(text)

    def _review(self):
        text = self._note_text()
        if text:
            self.reviewRequested.emit(text)


class ReviewCard(QFrame):
    sendRequested = Signal()
    addRequested = Signal()
    closeRequested = Signal()

    def __init__(self, annotations: list[Annotation], preview: QPixmap, parent=None):
        super().__init__(parent)
        self.setObjectName("reviewCard")
        self.setMinimumWidth(820)
        self.setMaximumWidth(1060)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        head = QHBoxLayout()
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title = QLabel("Review your annotations")
        title.setObjectName("reviewTitle")
        count = len(annotations)
        subtitle = QLabel(
            f"{count} change{'s' if count != 1 else ''} ready. Review the screenshot and comments before sending."
        )
        subtitle.setObjectName("muted")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        close = QPushButton("x")
        close.setObjectName("iconButton")
        close.setFixedSize(30, 30)
        close.clicked.connect(self.closeRequested)
        head.addLayout(title_stack)
        head.addStretch(1)
        head.addWidget(close)
        root.addLayout(head)

        body = QHBoxLayout()
        body.setSpacing(16)
        preview_card = QFrame()
        preview_card.setObjectName("previewCard")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        preview_label = QLabel()
        preview_label.setObjectName("previewImage")
        preview_label.setAlignment(Qt.AlignCenter)
        preview_label.setPixmap(
            preview.scaled(620, 390, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        preview_layout.addWidget(preview_label)
        body.addWidget(preview_card, 3)

        notes_card = QFrame()
        notes_card.setObjectName("notesCard")
        notes_layout = QVBoxLayout(notes_card)
        notes_layout.setContentsMargins(12, 12, 12, 12)
        notes_layout.setSpacing(8)
        notes_title = QLabel("Your comments")
        notes_title.setObjectName("sectionTitle")
        notes_layout.addWidget(notes_title)
        self.list = QListWidget()
        self.list.setObjectName("reviewList")
        self.list.setMinimumWidth(270)
        self.list.setMinimumHeight(260)
        for ann in annotations:
            item = QListWidgetItem(f"{ann.index}.  {ann.note}")
            item.setData(Qt.UserRole, ann.index)
            item.setToolTip(ann.note)
            self.list.addItem(item)
        notes_layout.addWidget(self.list, 1)
        body.addWidget(notes_card, 2)
        root.addLayout(body, 1)

        footer = QHBoxLayout()
        new_annotation = QPushButton("+ New Annotation")
        new_annotation.setObjectName("secondaryButton")
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        send = QPushButton(_send_button_label(_PENDING_SEND_ROUTE))
        send.setObjectName("sendButton")
        if SEND_ICON_PATH.exists():
            send.setIcon(QIcon(str(SEND_ICON_PATH)))
        send.setMinimumHeight(42)
        new_annotation.clicked.connect(self.addRequested)
        cancel.clicked.connect(self.closeRequested)
        send.clicked.connect(self._request_send)
        footer.addWidget(new_annotation)
        footer.addStretch(1)
        footer.addWidget(cancel)
        footer.addWidget(send)
        root.addLayout(footer)
        _add_send_route_menu(self, send)

    def _request_send(self):
        _apply_pending_send_route()
        self.sendRequested.emit()


class AnnotationOverlay(QWidget):
    finishedCapture = Signal(str, str, str)

    def __init__(self, settings: QSettings):
        super().__init__()
        self.settings = settings
        self.source_app, self.source_window = active_window_context()
        self.captured_at = datetime.now(timezone.utc)
        self.screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        self.snapshot = self.screen.grabWindow(0)
        self.screen_geometry = self.screen.geometry()
        self.dpr = float(self.screen.devicePixelRatio() or 1.0)
        self.setGeometry(self.screen_geometry)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)
        self.drag_start = None
        self.current_rect = None
        self.pending_rect = None
        self.annotations: list[Annotation] = []
        self.note_card = None
        self.review_card = None
        self.mode = "select"
        self.interaction = None
        self.interaction_start = None
        self.interaction_rect = None
        self.mode_pill = QLabel(
            "Annota   Annotation Mode   |   Drag to select   |   Esc to cancel", self
        )
        self.mode_pill.setObjectName("modePill")
        self.mode_pill.adjustSize()
        self.mode_pill.move(max(20, (self.width() - self.mode_pill.width()) // 2), 22)
        self.toolbar = QFrame(self)
        self.toolbar.setObjectName("toolbar")
        tl = QHBoxLayout(self.toolbar)
        tl.setContentsMargins(10, 8, 10, 8)
        tl.setSpacing(8)
        self.add_btn = QPushButton("+ New Annotation")
        self.review_btn = QPushButton("Review")
        self.send_btn = QPushButton("Auto Send")
        self.cancel_btn = QPushButton("Cancel")
        self.add_btn.setObjectName("toolbarButton")
        self.review_btn.setObjectName("toolbarButton")
        self.send_btn.setObjectName("toolbarPrimary")
        self.cancel_btn.setObjectName("toolbarButton")
        if SEND_ICON_PATH.exists():
            self.send_btn.setIcon(QIcon(str(SEND_ICON_PATH)))
        self.add_btn.clicked.connect(self._start_another)
        self.review_btn.clicked.connect(self._show_review)
        self.send_btn.clicked.connect(self._show_review)
        self.cancel_btn.clicked.connect(self.close)
        for widget in (self.add_btn, self.review_btn, self.send_btn, self.cancel_btn):
            tl.addWidget(widget)
        self.toolbar.adjustSize()
        self.toolbar.hide()
        self.setStyleSheet(APP_STYLE)
        _add_send_route_menu(self, self.send_btn)

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        _clear_pending_send_route()
        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.mode_pill.adjustSize()
        self.mode_pill.move(max(20, (self.width() - self.mode_pill.width()) // 2), 22)
        if self.toolbar.isVisible():
            self._position_toolbar()
        if self.review_card and self.review_card.isVisible():
            self._position_review()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.note_card:
                self._cancel_note()
            elif self.review_card:
                self._close_review()
            else:
                self.close()
            return
        if event.modifiers() & Qt.ControlModifier and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.annotations and not self.note_card:
                self._show_review()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or self.mode == "review":
            return
        pos = event.position().toPoint()
        if self.pending_rect and self.mode == "adjust":
            handle = self._hit_handle(self.pending_rect, pos)
            if handle:
                self.interaction = handle
                self.interaction_start = pos
                self.interaction_rect = QRect(self.pending_rect)
                return
            if self.pending_rect.contains(pos):
                self.interaction = "move"
                self.interaction_start = pos
                self.interaction_rect = QRect(self.pending_rect)
                self.setCursor(Qt.SizeAllCursor)
                return
            return
        if self.mode != "select":
            return
        self.drag_start = pos
        self.current_rect = QRect(pos, pos)
        self.update()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        if self.drag_start and self.mode == "select":
            self.current_rect = QRect(self.drag_start, pos).normalized().intersected(self.rect())
            self.update()
            return
        if (
            self.interaction
            and self.pending_rect
            and self.interaction_start
            and self.interaction_rect
        ):
            delta = pos - self.interaction_start
            if self.interaction == "move":
                r = QRect(self.interaction_rect)
                r.translate(delta)
                self.pending_rect = self._clamp_rect(r)
            else:
                self.pending_rect = self._resize_from_handle(
                    self.interaction_rect, self.interaction, pos
                )
            self._position_note_card()
            self.update()
            return
        if self.pending_rect and self.mode == "adjust":
            handle = self._hit_handle(self.pending_rect, pos)
            if handle in ("tl", "br"):
                self.setCursor(Qt.SizeFDiagCursor)
                return
            if handle in ("tr", "bl"):
                self.setCursor(Qt.SizeBDiagCursor)
                return
            if self.pending_rect.contains(pos):
                self.setCursor(Qt.SizeAllCursor)
                return
            self.setCursor(Qt.ArrowCursor)
            return
        if self.mode == "select":
            self.setCursor(Qt.CrossCursor)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        if self.interaction:
            self.interaction = None
            self.interaction_start = None
            self.interaction_rect = None
            self._position_note_card()
            return
        if self.mode != "select" or not self.drag_start:
            return
        rect = (
            QRect(self.drag_start, event.position().toPoint()).normalized().intersected(self.rect())
        )
        self.drag_start = None
        self.current_rect = None
        if rect.width() < MIN_SELECTION or rect.height() < MIN_SELECTION:
            self.update()
            return
        self.pending_rect = rect
        self.mode = "adjust"
        self.setCursor(Qt.ArrowCursor)
        self._show_note_card()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.snapshot)
        painter.fillRect(self.rect(), QColor(12, 13, 20, 112))
        painter.setPen(QPen(QColor(LAVENDER), 4))
        painter.drawRect(self.rect().adjusted(2, 2, -3, -3))
        for ann in self.annotations:
            self._paint_selection(painter, QRect(*ann.rect), ann.index)
        rect = self.current_rect or self.pending_rect
        if rect:
            self._paint_selection(painter, rect, len(self.annotations) + 1)
        if not rect and not self.annotations and self.mode == "select":
            center = self.rect().center()
            painter.setPen(QPen(QColor("white"), 3))
            painter.drawLine(center.x() - 18, center.y(), center.x() + 18, center.y())
            painter.drawLine(center.x(), center.y() - 18, center.x(), center.y() + 18)

    def _paint_selection(self, painter: QPainter, rect: QRect, number: int):
        painter.save()
        source = self._to_device_rect(rect)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.drawPixmap(rect, self.snapshot, source)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setPen(QPen(QColor(LAVENDER), 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 6, 6)
        handle = 9
        painter.setBrush(QColor("white"))
        painter.setPen(QPen(QColor(LAVENDER_DARK), 2))
        for pt in (rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()):
            painter.drawRect(pt.x() - handle // 2, pt.y() - handle // 2, handle, handle)
        marker_rect = QRect(rect.left() - 13, rect.top() - 13, 27, 27)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(LAVENDER_DARK))
        painter.drawEllipse(marker_rect)
        painter.setPen(QColor("white"))
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(marker_rect, Qt.AlignCenter, str(number))
        painter.restore()

    def _to_device_rect(self, rect: QRect) -> QRect:
        return QRect(
            round(rect.x() * self.dpr),
            round(rect.y() * self.dpr),
            max(1, round(rect.width() * self.dpr)),
            max(1, round(rect.height() * self.dpr)),
        )

    def _hit_handle(self, rect: QRect, pos: QPoint):
        points = {
            "tl": rect.topLeft(),
            "tr": rect.topRight(),
            "bl": rect.bottomLeft(),
            "br": rect.bottomRight(),
        }
        for name, pt in points.items():
            if abs(pos.x() - pt.x()) <= HANDLE_RADIUS and abs(pos.y() - pt.y()) <= HANDLE_RADIUS:
                return name
        return None

    def _resize_from_handle(self, original: QRect, handle: str, pos: QPoint) -> QRect:
        left, top, right, bottom = (
            original.left(),
            original.top(),
            original.right(),
            original.bottom(),
        )
        px = max(self.rect().left(), min(pos.x(), self.rect().right()))
        py = max(self.rect().top(), min(pos.y(), self.rect().bottom()))
        if handle == "tl":
            left = min(px, right - MIN_SELECTION)
            top = min(py, bottom - MIN_SELECTION)
        elif handle == "tr":
            right = max(px, left + MIN_SELECTION)
            top = min(py, bottom - MIN_SELECTION)
        elif handle == "bl":
            left = min(px, right - MIN_SELECTION)
            bottom = max(py, top + MIN_SELECTION)
        elif handle == "br":
            right = max(px, left + MIN_SELECTION)
            bottom = max(py, top + MIN_SELECTION)
        return QRect(QPoint(left, top), QPoint(right, bottom)).normalized().intersected(self.rect())

    def _clamp_rect(self, rect: QRect) -> QRect:
        result = QRect(rect)
        bounds = self.rect()
        if result.left() < bounds.left():
            result.moveLeft(bounds.left())
        if result.top() < bounds.top():
            result.moveTop(bounds.top())
        if result.right() > bounds.right():
            result.moveRight(bounds.right())
        if result.bottom() > bounds.bottom():
            result.moveBottom(bounds.bottom())
        return result

    def _show_note_card(self):
        if not self.pending_rect:
            return
        self.note_card = NoteCard(len(self.annotations) + 1, self)
        self.note_card.newAnnotationRequested.connect(self._save_and_new)
        self.note_card.reviewRequested.connect(self._save_and_review)
        self.note_card.cancelRequested.connect(self._cancel_note)
        self.note_card.adjustSize()
        self._position_note_card()
        self.note_card.show()
        self.note_card.raise_()
        _diagnostic_event(
            "note_card_shown",
            number=len(self.annotations) + 1,
            controls=_widget_diagnostic_controls(self.note_card),
        )
        QTimer.singleShot(0, self.note_card.editor.setFocus)

    def _position_note_card(self):
        if not self.pending_rect or not self.note_card:
            return
        self.note_card.adjustSize()
        gap = 14
        x = self.pending_rect.right() + gap
        if x + self.note_card.width() > self.width() - 16:
            x = max(16, self.pending_rect.left() - self.note_card.width() - gap)
        y = min(max(70, self.pending_rect.top()), self.height() - self.note_card.height() - 24)
        self.note_card.move(x, y)
        self.note_card.raise_()

    def _commit_pending_note(self, note: str) -> bool:
        if not self.pending_rect:
            return False
        rect = self.pending_rect
        self.annotations.append(
            Annotation(
                len(self.annotations) + 1,
                (rect.x(), rect.y(), rect.width(), rect.height()),
                note,
            )
        )
        _diagnostic_event(
            "annotation_committed",
            index=len(self.annotations),
            rect=[rect.x(), rect.y(), rect.width(), rect.height()],
            note_length=len(note),
        )
        if self.note_card:
            self.note_card.close()
            self.note_card = None
        self.pending_rect = None
        self.interaction = None
        self.update()
        return True

    def _save_and_new(self, note: str):
        if not self._commit_pending_note(note):
            return
        self.mode = "select"
        self.setCursor(Qt.CrossCursor)
        self.toolbar.hide()
        self.update()

    def _save_and_review(self, note: str):
        if not self._commit_pending_note(note):
            return
        self.toolbar.hide()
        self._show_review()

    def _cancel_note(self):
        if self.note_card:
            self.note_card.close()
            self.note_card = None
        self.pending_rect = None
        self.mode = "select"
        self.interaction = None
        self.setCursor(Qt.CrossCursor)
        if self.annotations:
            _set_pending_send_route(_PENDING_SEND_ROUTE, self.send_btn)
            self._position_toolbar()
            self.toolbar.show()
        else:
            self.toolbar.hide()
        self.update()

    def _position_toolbar(self):
        self.toolbar.adjustSize()
        self.toolbar.move(
            max(20, (self.width() - self.toolbar.width()) // 2),
            self.height() - self.toolbar.height() - 24,
        )

    def _start_another(self):
        if self.review_card:
            self.review_card.close()
            self.review_card = None
        self.mode = "select"
        self.setCursor(Qt.CrossCursor)
        self.toolbar.hide()
        self.update()

    def _make_review_preview(self) -> QPixmap:
        preview = self.snapshot.copy()
        painter = QPainter(preview)
        scale = self.dpr
        for ann in self.annotations:
            logical = QRect(*ann.rect)
            rect = QRect(
                round(logical.x() * scale),
                round(logical.y() * scale),
                max(1, round(logical.width() * scale)),
                max(1, round(logical.height() * scale)),
            )
            painter.setPen(QPen(QColor(LAVENDER_DARK), max(3, round(4 * scale))))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, round(6 * scale), round(6 * scale))
            marker_size = max(26, round(28 * scale))
            marker = QRect(
                rect.left() - marker_size // 2,
                rect.top() - marker_size // 2,
                marker_size,
                marker_size,
            )
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(LAVENDER_DARK))
            painter.drawEllipse(marker)
            painter.setPen(QColor("white"))
            font = painter.font()
            font.setBold(True)
            font.setPixelSize(max(12, round(13 * scale)))
            painter.setFont(font)
            painter.drawText(marker, Qt.AlignCenter, str(ann.index))
        painter.end()
        return preview

    def _show_review(self):
        if not self.annotations or self.note_card:
            return
        if self.review_card:
            self.review_card.close()
        self.review_card = ReviewCard(self.annotations, self._make_review_preview(), self)
        self.review_card.sendRequested.connect(self._send)
        self.review_card.addRequested.connect(self._start_another)
        self.review_card.closeRequested.connect(self._close_review)
        self.review_card.adjustSize()
        self._position_review()
        self.review_card.show()
        self.review_card.raise_()
        _diagnostic_event(
            "review_shown",
            annotation_count=len(self.annotations),
            controls=_widget_diagnostic_controls(self.review_card),
        )
        self.mode = "review"
        self.setCursor(Qt.ArrowCursor)

    def _position_review(self):
        if not self.review_card:
            return
        self.review_card.adjustSize()
        max_width = max(720, self.width() - 80)
        self.review_card.setMaximumWidth(min(1060, max_width))
        self.review_card.adjustSize()
        x = max(24, (self.width() - self.review_card.width()) // 2)
        y = max(60, (self.height() - self.review_card.height()) // 2)
        self.review_card.move(x, y)

    def _close_review(self):
        if self.review_card:
            self.review_card.close()
            self.review_card = None
        self.mode = "select"
        self.setCursor(Qt.CrossCursor)
        if self.annotations:
            _set_pending_send_route(_PENDING_SEND_ROUTE, self.send_btn)
            self._position_toolbar()
            self.toolbar.show()

    def _send(self):
        if not self.annotations:
            return
        if not self.review_card or not self.review_card.isVisible():
            self._show_review()
            return
        path, message, meta_path = self._build_payload()
        _diagnostic_event(
            "payload_ready",
            image=path,
            metadata=meta_path,
            annotation_count=len(self.annotations),
        )
        self.finishedCapture.emit(path, message, meta_path)
        _clear_pending_send_route()
        self.close()

    def _build_payload(self) -> tuple[str, str, str]:
        padding_pct = int(self.settings.value("behavior/context_padding", 15))
        union = None
        for ann in self.annotations:
            rect = QRect(*ann.rect)
            union = QRect(rect) if union is None else union.united(rect)
        assert union is not None
        pad_x = max(24, int(union.width() * padding_pct / 100))
        pad_y = max(24, int(union.height() * padding_pct / 100))
        crop = union.adjusted(-pad_x, -pad_y, pad_x, pad_y).intersected(self.rect())
        canvas = self.snapshot.copy(self._to_device_rect(crop))
        painter = QPainter(canvas)
        scale = self.dpr
        for ann in self.annotations:
            logical = QRect(*ann.rect).translated(-crop.topLeft())
            rect = QRect(
                round(logical.x() * scale),
                round(logical.y() * scale),
                max(1, round(logical.width() * scale)),
                max(1, round(logical.height() * scale)),
            )
            painter.setPen(QPen(QColor(LAVENDER_DARK), max(3, round(4 * scale))))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, round(6 * scale), round(6 * scale))
            marker_size = max(26, round(27 * scale))
            marker = QRect(
                rect.left() - marker_size // 2,
                rect.top() - marker_size // 2,
                marker_size,
                marker_size,
            )
            painter.setBrush(QColor(LAVENDER_DARK))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(marker)
            painter.setPen(QColor("white"))
            font = painter.font()
            font.setBold(True)
            font.setPixelSize(max(12, round(13 * scale)))
            painter.setFont(font)
            painter.drawText(marker, Qt.AlignCenter, str(ann.index))
        painter.end()
        tmp_dir = Path(tempfile.gettempdir()) / "Annota"
        tmp_dir.mkdir(exist_ok=True)
        image_path = tmp_dir / "latest-annotation.png"
        meta_path = tmp_dir / "latest-annotation.json"
        text_path = tmp_dir / "latest-annotation.txt"
        canvas.save(str(image_path), "PNG")
        logical_size = f"{self.screen_geometry.width()}x{self.screen_geometry.height()}"
        timestamp = datetime.now(timezone.utc).isoformat()
        message_lines = [
            "UI annotation from Annota",
            f"Application: {self.source_app}",
            f"Window: {self.source_window}",
            f"Display: {logical_size}",
            f"DPI scale: {self.dpr:.2f}x",
            f"Timestamp: {timestamp}",
            "",
        ]
        for ann in self.annotations:
            message_lines.append(f"{ann.index}. {ann.note}")
        message_lines += [
            "",
            "Use the highlighted regions as the visual source of truth. Inspect the relevant code, implement these fixes, build and test locally, and visually verify the result.",
        ]
        message = "\n".join(message_lines)
        text_path.write_text(message, encoding="utf-8")
        annotations_meta = []
        for ann in self.annotations:
            item = asdict(ann)
            x, y, width, height = ann.rect
            item["screen_rect"] = [
                x + self.screen_geometry.x(),
                y + self.screen_geometry.y(),
                width,
                height,
            ]
            annotations_meta.append(item)
        metadata = {
            "schema": 3,
            "application": self.source_app,
            "window_title": self.source_window,
            "display": logical_size,
            "display_geometry": [
                self.screen_geometry.x(),
                self.screen_geometry.y(),
                self.screen_geometry.width(),
                self.screen_geometry.height(),
            ],
            "device_pixel_ratio": self.dpr,
            "context_padding_percent": padding_pct,
            "captured_at": self.captured_at.isoformat(),
            "payload_created_at": timestamp,
            "annotations": annotations_meta,
            "image": str(image_path),
            "notes": str(text_path),
        }
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return str(image_path), message, str(meta_path)


def is_macos() -> bool:
    return platform.system() == "Darwin"


def macos_permission_status() -> dict[str, bool]:
    status = {"screen_recording": True, "accessibility": True, "post_events": True}
    if not is_macos():
        return status
    status = {"screen_recording": False, "accessibility": False, "post_events": False}
    try:
        import Quartz

        status["screen_recording"] = bool(Quartz.CGPreflightScreenCaptureAccess())
        check_post = getattr(Quartz, "CGPreflightPostEventAccess", None)
        status["post_events"] = bool(check_post()) if check_post else False
    except Exception:
        pass
    try:
        import HIServices

        status["accessibility"] = bool(HIServices.AXIsProcessTrusted())
    except Exception:
        pass
    return status


def macos_automatic_paste_ready(status: dict[str, bool] | None = None) -> bool:
    """Return whether macOS currently allows Annota to post paste key events."""
    if not is_macos():
        return True
    current = status or macos_permission_status()
    return bool(current.get("accessibility") or current.get("post_events"))


def macos_post_paste_shortcut() -> tuple[bool, str]:
    """Post Cmd+V with Quartz and report whether the request could be issued.

    This deliberately avoids pynput on macOS. Quartz uses the app's native
    Accessibility/Post Event permission and lets Annota distinguish a blocked
    paste request from a request that was successfully posted to macOS.
    """
    if not is_macos():
        return False, "Native macOS paste is unavailable on this platform"

    status = macos_permission_status()
    if not macos_automatic_paste_ready(status):
        return False, "Accessibility permission is not available for automatic paste"

    try:
        import Quartz

        key_code_v = 9
        key_down = Quartz.CGEventCreateKeyboardEvent(None, key_code_v, True)
        key_up = Quartz.CGEventCreateKeyboardEvent(None, key_code_v, False)
        if key_down is None or key_up is None:
            return False, "macOS could not create a paste keyboard event"
        Quartz.CGEventSetFlags(key_down, Quartz.kCGEventFlagMaskCommand)
        Quartz.CGEventSetFlags(key_up, Quartz.kCGEventFlagMaskCommand)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, key_down)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, key_up)
        return True, ""
    except Exception as exc:
        return False, f"macOS paste event failed: {exc}"


def macos_request_screen_recording() -> bool:
    if not is_macos():
        return True
    try:
        import Quartz

        return bool(Quartz.CGRequestScreenCaptureAccess())
    except Exception:
        return False


def macos_request_accessibility() -> bool:
    if not is_macos():
        return True
    result = False
    try:
        import HIServices

        prompt_key = getattr(HIServices, "kAXTrustedCheckOptionPrompt", None)
        if prompt_key is not None:
            result = bool(HIServices.AXIsProcessTrustedWithOptions({prompt_key: True}))
        else:
            result = bool(HIServices.AXIsProcessTrusted())
    except Exception:
        pass
    try:
        import Quartz

        request_post = getattr(Quartz, "CGRequestPostEventAccess", None)
        if request_post is not None:
            request_post()
    except Exception:
        pass
    return result


def open_macos_privacy_pane(kind: str) -> None:
    if not is_macos():
        return
    urls = {
        "screen": "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
        "accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
    }
    QDesktopServices.openUrl(QUrl(urls.get(kind, urls["accessibility"])))


def macos_frontmost_app() -> dict:
    if not is_macos():
        return {}
    try:
        from AppKit import NSWorkspace

        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return {}
        return {
            "pid": int(app.processIdentifier()),
            "name": str(app.localizedName() or ""),
            "bundle_id": str(app.bundleIdentifier() or ""),
        }
    except Exception:
        return {}


def classify_macos_app(target: dict) -> str | None:
    name = str(target.get("name", "")).lower()
    bundle_id = str(target.get("bundle_id", "")).lower()
    value = f"{name} {bundle_id}"
    if "codex" in value:
        return "codex"
    if "chatgpt" in value or "openai" in value:
        return "chatgpt_desktop"
    browsers = ("safari", "chrome", "firefox", "edge", "brave", "arc", "opera", "vivaldi")
    if any(browser in value for browser in browsers):
        return "chatgpt_web"
    return None


def macos_find_chat_target(route: str | None = None, source_target: dict | None = None) -> dict:
    if not is_macos() or route == "clipboard":
        return {}
    source_target = source_target or {}
    source_route = classify_macos_app(source_target)
    wanted = ROUTE_PRIORITY if route in (None, "auto") else (route,)
    if source_route in wanted and (source_route != "chatgpt_web" or route == "chatgpt_web"):
        return source_target
    try:
        from AppKit import NSWorkspace

        found = []
        for app in NSWorkspace.sharedWorkspace().runningApplications():
            target = {
                "pid": int(app.processIdentifier()),
                "name": str(app.localizedName() or ""),
                "bundle_id": str(app.bundleIdentifier() or ""),
            }
            detected = classify_macos_app(target)
            if detected in ("codex", "chatgpt_desktop"):
                target["route"] = detected
                found.append(target)
        for wanted_route in wanted:
            for target in found:
                if target.get("route") == wanted_route:
                    return target
    except Exception:
        pass
    return {}


def focus_macos_app(target: dict) -> bool:
    if not is_macos() or not target:
        return False
    try:
        from AppKit import NSApplicationActivateIgnoringOtherApps, NSRunningApplication

        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(
            int(target.get("pid", 0))
        )
        return bool(app and app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps))
    except Exception:
        return False


def configure_macos_startup(enabled: bool) -> None:
    if not is_macos():
        return
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    plist_path = launch_agents / "net.softwify.annota.plist"
    if not enabled:
        with suppress(FileNotFoundError):
            plist_path.unlink()
        return
    launch_agents.mkdir(parents=True, exist_ok=True)
    executable = str(Path(sys.executable).resolve())
    program_arguments = [executable]
    if not getattr(sys, "frozen", False):
        program_arguments.append(str(Path(__file__).resolve()))
    data = {
        "Label": "net.softwify.annota",
        "ProgramArguments": program_arguments,
        "RunAtLoad": True,
        "KeepAlive": False,
        "ProcessType": "Interactive",
    }
    with plist_path.open("wb") as handle:
        plistlib.dump(data, handle)


class MacSetupDialog(QDialog):
    startRequested = Signal()
    settingsRequested = Signal()
    permissionsChanged = Signal()

    def __init__(self, shortcut: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Annota for macOS")
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.setMinimumWidth(600)
        self.setStyleSheet(APP_STYLE)
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 24)
        root.setSpacing(14)
        title = QLabel("Annota is running")
        title.setObjectName("dialogTitle")
        root.addWidget(title)
        intro = QLabel(
            "Start an annotation from this window or the Annota menu-bar icon. macOS permissions are checked here so the app never fails silently."
        )
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        root.addWidget(intro)
        self.shortcut_status = QLabel(f"Quick Capture Shortcut: {shortcut}  -  starting...")
        self.screen_status = QLabel()
        self.access_status = QLabel()
        self.send_status = QLabel()
        root.addWidget(self.shortcut_status)
        root.addWidget(self.screen_status)
        root.addWidget(self.access_status)
        root.addWidget(self.send_status)

        screen_row = QHBoxLayout()
        allow_screen = QPushButton("Allow Screen Recording")
        allow_screen.setObjectName("secondaryButton")
        open_screen = QPushButton("Open Screen Recording Settings")
        open_screen.setObjectName("secondaryButton")
        allow_screen.clicked.connect(self._request_screen)
        open_screen.clicked.connect(lambda: open_macos_privacy_pane("screen"))
        screen_row.addWidget(allow_screen)
        screen_row.addWidget(open_screen)
        root.addLayout(screen_row)

        access_row = QHBoxLayout()
        allow_access = QPushButton("Allow Accessibility")
        allow_access.setObjectName("secondaryButton")
        open_access = QPushButton("Open Accessibility Settings")
        open_access.setObjectName("secondaryButton")
        allow_access.clicked.connect(self._request_access)
        open_access.clicked.connect(lambda: open_macos_privacy_pane("accessibility"))
        access_row.addWidget(allow_access)
        access_row.addWidget(open_access)
        root.addLayout(access_row)

        note = QLabel(
            "Quick Capture uses a native macOS global shortcut. Automatic send uses native Quartz paste events and falls back to the clipboard if macOS or the target app blocks insertion."
        )
        note.setObjectName("muted")
        note.setWordWrap(True)
        root.addWidget(note)
        footer = QHBoxLayout()
        settings = QPushButton("Settings")
        settings.setObjectName("secondaryButton")
        refresh = QPushButton("Refresh")
        refresh.setObjectName("secondaryButton")
        annotate = QPushButton("Start Annotation")
        annotate.setObjectName("primaryButton")
        settings.clicked.connect(self.settingsRequested)
        refresh.clicked.connect(self._refresh)
        annotate.clicked.connect(self.startRequested)
        footer.addWidget(settings)
        footer.addWidget(refresh)
        footer.addStretch(1)
        footer.addWidget(annotate)
        root.addLayout(footer)
        self._refresh()

    def _request_screen(self):
        macos_request_screen_recording()
        QTimer.singleShot(400, self._refresh)

    def _request_access(self):
        macos_request_accessibility()
        QTimer.singleShot(400, self._refresh)

    def _refresh(self):
        status = macos_permission_status()
        self.screen_status.setText(
            f"Screen Recording: {'Ready' if status['screen_recording'] else 'Permission required'}"
        )
        paste_ready = macos_automatic_paste_ready(status)
        self.access_status.setText(
            f"Accessibility / keyboard events: {'Ready' if paste_ready else 'Permission required for automatic paste'}"
        )
        self.send_status.setText(
            "Automatic send: Ready to attempt native paste"
            if paste_ready
            else "Automatic send: Clipboard fallback will be used until permission is available"
        )
        self.permissionsChanged.emit()

    def set_shortcut_status(self, text: str):
        self.shortcut_status.setText(f"Quick Capture Shortcut: {text}")


class SettingsDialog(QDialog):
    shortcutChanged = Signal(str)
    pauseChanged = Signal(bool)

    def __init__(self, settings: QSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Annota Settings")
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.setMinimumWidth(590)
        self.setStyleSheet(APP_STYLE)
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 24)
        root.setSpacing(16)
        title = QLabel("Settings")
        title.setObjectName("dialogTitle")
        root.addWidget(title)
        subtitle = QLabel("Keep Annota fast, quiet, and ready when you need it.")
        subtitle.setObjectName("muted")
        root.addWidget(subtitle)
        shortcut_card = QFrame()
        shortcut_card.setObjectName("settingsCard")
        shortcut_layout = QVBoxLayout(shortcut_card)
        shortcut_layout.setContentsMargins(16, 14, 16, 14)
        shortcut_layout.setSpacing(9)
        shortcut_label = QLabel("Quick Capture Shortcut")
        shortcut_label.setObjectName("sectionTitle")
        hint = QLabel(
            "Change the global shortcut used to start a capture. On macOS the packaged app uses a native system hotkey, so Accessibility is not required just to trigger capture."
        )
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        shortcut_layout.addWidget(shortcut_label)
        shortcut_layout.addWidget(hint)
        row = QHBoxLayout()
        self.shortcut = QLineEdit(self.settings.value("shortcut", default_shortcut()))
        self.shortcut.setPlaceholderText(default_shortcut())
        reset = QPushButton("Reset")
        reset.setObjectName("secondaryButton")
        reset.clicked.connect(lambda: self.shortcut.setText(default_shortcut()))
        row.addWidget(self.shortcut, 1)
        row.addWidget(reset)
        shortcut_layout.addLayout(row)
        root.addWidget(shortcut_card)
        behavior_card = QFrame()
        behavior_card.setObjectName("settingsCard")
        behavior_layout = QVBoxLayout(behavior_card)
        behavior_layout.setContentsMargins(16, 14, 16, 14)
        behavior_layout.setSpacing(10)
        behavior = QLabel("Behavior")
        behavior.setObjectName("sectionTitle")
        behavior_layout.addWidget(behavior)
        self.start_login = QCheckBox("Start at login" if is_macos() else "Start with Windows")
        self.start_login.setChecked(
            self.settings.value("behavior/start_at_login", False, type=bool)
        )
        self.pause_shortcut = QCheckBox("Pause global shortcut")
        self.pause_shortcut.setChecked(
            self.settings.value("behavior/pause_shortcut", False, type=bool)
        )
        if is_macos():
            self.clear_after = QCheckBox(
                "Keep notes on clipboard after automatic paste (macOS safety fallback)"
            )
            self.clear_after.setChecked(True)
            self.clear_after.setEnabled(False)
            self.clear_after.setToolTip(
                "macOS does not provide reliable confirmation that another app accepted synthetic paste, so Annota keeps the notes available for Command+V."
            )
        else:
            self.clear_after = QCheckBox("Clear clipboard after insertion")
            self.clear_after.setChecked(
                self.settings.value("behavior/clear_after_send", True, type=bool)
            )
        behavior_layout.addWidget(self.start_login)
        behavior_layout.addWidget(self.pause_shortcut)
        behavior_layout.addWidget(self.clear_after)
        pad_row = QHBoxLayout()
        pad_row.addWidget(QLabel("Context padding"))
        self.padding = QSpinBox()
        self.padding.setRange(0, 50)
        self.padding.setSuffix("%")
        self.padding.setValue(int(self.settings.value("behavior/context_padding", 15)))
        pad_row.addStretch(1)
        pad_row.addWidget(self.padding)
        behavior_layout.addLayout(pad_row)
        root.addWidget(behavior_card)
        about_card = QFrame()
        about_card.setObjectName("settingsCard")
        about_layout = QVBoxLayout(about_card)
        about_layout.setContentsMargins(16, 14, 16, 14)
        about_layout.setSpacing(5)
        about_title = QLabel("About")
        about_title.setObjectName("sectionTitle")
        about_layout.addWidget(about_title)
        about_layout.addWidget(QLabel(f"Annota {APP_VERSION}  |  SoftWify  |  MIT License"))
        privacy = QLabel(
            "Local-first: no telemetry, no account, no continuous recording, and no cloud dependency."
        )
        privacy.setObjectName("muted")
        privacy.setWordWrap(True)
        about_layout.addWidget(privacy)
        root.addWidget(about_card)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        save = QPushButton("Save settings")
        save.setObjectName("primaryButton")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        root.addLayout(buttons)

    def _save(self):
        shortcut = normalize_shortcut(self.shortcut.text().strip())
        if not shortcut:
            QMessageBox.warning(
                self, APP_NAME, f"Enter a valid shortcut such as {default_shortcut()}."
            )
            return
        if is_macos() and not macos_hotkey_supported(shortcut):
            QMessageBox.warning(
                self,
                APP_NAME,
                "On macOS, Quick Capture currently supports A-Z, 0-9, and F1-F20 with Option, Ctrl, Shift, or Cmd modifiers.",
            )
            return
        current = normalize_shortcut(str(self.settings.value("shortcut", default_shortcut())))
        if shortcut != current and shortcut_conflicts(shortcut):
            QMessageBox.warning(
                self,
                APP_NAME,
                f"{shortcut} appears to be in use by the operating system or another application. Choose a different shortcut.",
            )
            return
        self.settings.setValue("shortcut", shortcut)
        self.settings.setValue("behavior/start_at_login", self.start_login.isChecked())
        self.settings.setValue("behavior/pause_shortcut", self.pause_shortcut.isChecked())
        self.settings.setValue("behavior/clear_after_send", self.clear_after.isChecked())
        self.settings.setValue("behavior/context_padding", self.padding.value())
        configure_startup(self.start_login.isChecked())
        self.shortcutChanged.emit(shortcut)
        self.pauseChanged.emit(self.pause_shortcut.isChecked())
        self.accept()


class GlobalHotkey:
    def __init__(self, callback: Callable):
        self.callback = callback
        self.listener = None
        self.sequence = ""
        self.mac_process = None
        self.mac_ready = False
        self.last_error = ""
        self._generation = 0

    def set_sequence(self, sequence: str):
        self.stop()
        self.sequence = normalize_shortcut(str(sequence)) or str(sequence)
        self.last_error = ""
        self._generation += 1
        generation = self._generation

        if is_macos() and HOTKEY_HELPER_PATH.exists():
            try:
                process = subprocess.Popen(
                    [str(HOTKEY_HELPER_PATH), self.sequence],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )
                self.mac_process = process
                threading.Thread(
                    target=self._monitor_macos_helper,
                    args=(process, generation),
                    daemon=True,
                ).start()
                return
            except Exception as exc:
                self.last_error = f"Native shortcut helper failed to start: {exc}"
                self.mac_process = None

        if keyboard is None:
            if not self.last_error:
                self.last_error = "Keyboard backend unavailable"
            return
        spec = to_pynput_hotkey(self.sequence)
        if not spec:
            self.last_error = "Invalid shortcut"
            return
        try:
            self.listener = keyboard.GlobalHotKeys({spec: self.callback})
            self.listener.start()
        except Exception as exc:
            self.listener = None
            self.last_error = f"Shortcut listener failed: {exc}"

    def _monitor_macos_helper(self, process, generation: int):
        if process.stdout is None:
            return
        try:
            for raw in process.stdout:
                line = raw.strip()
                if line.startswith("READY"):
                    if self.mac_process is process and self._generation == generation:
                        self.mac_ready = True
                        self.last_error = ""
                elif (
                    line == "TRIGGER"
                    and self.mac_process is process
                    and self._generation == generation
                ):
                    self.callback()
        finally:
            if self.mac_process is process and self._generation == generation:
                error = ""
                if process.stderr is not None:
                    error = process.stderr.read().strip().replace("ERROR ", "")
                if error:
                    self.last_error = error
                elif self.mac_ready:
                    self.last_error = "Native shortcut helper stopped unexpectedly"
                self.mac_ready = False

    def status_text(self) -> str:
        if not self.sequence:
            return "Not configured"
        if self.mac_ready and self.mac_process is not None and self.mac_process.poll() is None:
            return f"{self.sequence} - Active (native macOS)"
        if self.listener is not None:
            return f"{self.sequence} - Active"
        if self.last_error:
            return f"{self.sequence} - {self.last_error}"
        return f"{self.sequence} - Starting..."

    def stop(self):
        self._generation += 1
        self.mac_ready = False
        process = self.mac_process
        self.mac_process = None
        if process is not None:
            try:
                process.terminate()
                process.wait(timeout=1.5)
            except (OSError, subprocess.TimeoutExpired):
                with suppress(OSError):
                    process.kill()
        if self.listener:
            with suppress(Exception):
                self.listener.stop()
            self.listener = None


class AnnotaApp:
    def __init__(self, qt_app: QApplication):
        self.app = qt_app
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName(APP_NAME)
        self.app.setOrganizationName(ORG_NAME)
        self.settings = QSettings(ORG_NAME, APP_NAME)
        self.overlay = None
        self.settings_dialog = None
        self.mac_setup_dialog = None
        self.last_source_target = {}
        self.toast = None
        self._last_hotkey_error = ""
        self.tray = QSystemTrayIcon(QIcon(str(ICON_PATH)), self.app)
        self.tray.setToolTip("Annota - Quick desktop annotation")
        self.tray_menu = QMenu()
        self.annotate_action = QAction("", self.tray_menu)
        self.annotate_action.triggered.connect(lambda: self.activate_annotation(force=True))
        settings_action = QAction("Settings", self.tray_menu)
        settings_action.triggered.connect(self.open_settings)
        self.pause_action = QAction("Pause Shortcut", self.tray_menu)
        self.pause_action.setCheckable(True)
        about = QAction("About", self.tray_menu)
        about.triggered.connect(self.show_about)
        quit_action = QAction("Quit", self.tray_menu)
        quit_action.triggered.connect(self.quit)
        self.tray_menu.addAction(self.annotate_action)
        if is_macos():
            self.mac_setup_action = QAction("Permissions & Setup", self.tray_menu)
            self.mac_setup_action.triggered.connect(self.open_macos_setup)
            self.tray_menu.addAction(self.mac_setup_action)
        self.tray_menu.addAction(settings_action)
        self.tray_menu.addAction(self.pause_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(about)
        self.tray_menu.addAction(quit_action)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()
        _diagnostic_event(
            "app_ready",
            shortcut=str(self.settings.value("shortcut", default_shortcut())),
            paused=self.settings.value("behavior/pause_shortcut", False, type=bool),
        )
        self.hotkey_bridge = HotkeyBridge(self.app)
        self.hotkey_bridge.activated.connect(self.activate_annotation)
        self.hotkey = GlobalHotkey(self.hotkey_bridge.activated.emit)
        self._update_annotate_action()
        self.pause_action.toggled.connect(self._pause_hotkey)
        paused = self.settings.value("behavior/pause_shortcut", False, type=bool)
        self.pause_action.setChecked(paused)
        if not paused:
            self.hotkey.set_sequence(self.settings.value("shortcut", default_shortcut()))
        if self.settings.value("behavior/start_at_login", False, type=bool):
            configure_startup(True)
        self._annota_command_timer = QTimer(self.app)
        self._annota_command_timer.setInterval(150)
        self._annota_command_timer.timeout.connect(lambda: _drain_instance_commands(self))
        self._annota_command_timer.start()
        self._mac_status_timer = None
        if is_macos():
            self._mac_status_timer = QTimer(self.app)
            self._mac_status_timer.setInterval(750)
            self._mac_status_timer.timeout.connect(self._refresh_macos_hotkey_status)
            self._mac_status_timer.start()
            if not os.environ.get("ANNOTA_CI_SMOKE"):
                QTimer.singleShot(450, self._show_macos_setup_if_needed)
        if _INITIAL_QUICK_ANNOTATE:
            QTimer.singleShot(180, lambda: self.activate_annotation(force=True))

    def _show_toast(self, title: str, detail: str, milliseconds: int = 4200):
        if self.toast:
            self.toast.close()
        self.toast = StatusToast(title, detail)
        self.toast.show_for(milliseconds)

    def _update_annotate_action(self):
        sequence = str(self.settings.value("shortcut", default_shortcut()))
        self.annotate_action.setText(f"Annotate Now    {sequence}")

    def _tray_activated(self, reason):
        if tray_click_starts_annotation(reason):
            self.activate_annotation(force=True)

    def _show_macos_setup_if_needed(self):
        status = macos_permission_status()
        first_run = not self.settings.value("macos/setup_seen", False, type=bool)
        if first_run or not status["screen_recording"]:
            self.open_macos_setup()

    def open_macos_setup(self):
        if not is_macos():
            return
        if self.mac_setup_dialog and self.mac_setup_dialog.isVisible():
            self.mac_setup_dialog.raise_()
            self.mac_setup_dialog.activateWindow()
            return
        self.settings.setValue("macos/setup_seen", True)
        sequence = str(self.settings.value("shortcut", default_shortcut()))
        self.mac_setup_dialog = MacSetupDialog(sequence)
        self.mac_setup_dialog.startRequested.connect(lambda: self.activate_annotation(force=True))
        self.mac_setup_dialog.settingsRequested.connect(self.open_settings)
        self.mac_setup_dialog.permissionsChanged.connect(self._refresh_macos_permissions)
        self.mac_setup_dialog.show()
        self.mac_setup_dialog.raise_()
        self.mac_setup_dialog.activateWindow()
        QTimer.singleShot(500, self._refresh_macos_hotkey_status)

    def _refresh_macos_permissions(self):
        if not is_macos():
            return
        self._refresh_macos_hotkey_status()

    def _refresh_macos_hotkey_status(self):
        if not is_macos():
            return
        if self.mac_setup_dialog and self.mac_setup_dialog.isVisible():
            if self.pause_action.isChecked():
                sequence = str(self.settings.value("shortcut", default_shortcut()))
                status_text = f"{sequence} - Paused"
            else:
                status_text = self.hotkey.status_text()
            self.mac_setup_dialog.set_shortcut_status(status_text)
        error = "" if self.pause_action.isChecked() else self.hotkey.last_error
        if error and error != self._last_hotkey_error and not os.environ.get("ANNOTA_CI_SMOKE"):
            self._last_hotkey_error = error
            self._show_toast(
                "Quick Capture shortcut unavailable",
                f"{error}. Open Settings and choose another Quick Capture shortcut.",
                6500,
            )
        elif not error:
            self._last_hotkey_error = ""

    def activate_annotation(self, force: bool = False):
        _diagnostic_event(
            "activate_annotation",
            force=force,
            paused=self.pause_action.isChecked(),
        )
        if self.pause_action.isChecked() and not force:
            _diagnostic_event("activation_ignored_paused")
            return
        if is_macos() and not os.environ.get("ANNOTA_CI_SMOKE"):
            status = macos_permission_status()
            if not status["screen_recording"]:
                macos_request_screen_recording()
                self.open_macos_setup()
                self._show_toast(
                    "Screen Recording permission needed",
                    "Allow Annota in Privacy & Security > Screen Recording, then click Start Annotation again.",
                    6500,
                )
                return
        if self.overlay and self.overlay.isVisible():
            self.overlay.raise_()
            self.overlay.activateWindow()
            return
        self.last_source_target = macos_frontmost_app() if is_macos() else {}
        self.overlay = AnnotationOverlay(self.settings)
        self.overlay.finishedCapture.connect(self.handle_capture)
        self.overlay.show()
        self.overlay.raise_()
        self.overlay.activateWindow()
        _diagnostic_event(
            "overlay_shown",
            geometry=[
                self.overlay.x(),
                self.overlay.y(),
                self.overlay.width(),
                self.overlay.height(),
            ],
        )

    def handle_capture(self, image_path: str, message: str, meta_path: str):
        self._show_toast(
            "Sending to current chat",
            "Annota is inserting the screenshot first, then the matching notes.",
            2600,
        )
        self._send_to_current_chat(image_path, message)

    def _copy_for_manual_paste(
        self,
        image_path: str,
        message: str,
        detail: str,
        milliseconds: int = 6200,
    ) -> None:
        clipboard_fallback(image_path, message)
        self._show_toast("Copied for manual paste", detail, milliseconds)

    def _send_to_current_chat(self, image_path: str, message: str):
        global _SEND_ROUTE_OVERRIDE
        route = _SEND_ROUTE_OVERRIDE
        route_was_clipboard = route == "clipboard"
        _SEND_ROUTE_OVERRIDE = None

        if is_macos():
            target = (
                {}
                if route_was_clipboard
                else macos_find_chat_target(route, self.last_source_target)
            )
            if not target:
                detail = (
                    "The annotated image and notes are on the clipboard and saved in your temporary Annota folder."
                    if route_was_clipboard
                    else "No safe macOS chat target was available. The annotated image and notes were copied for manual paste."
                )
                self._copy_for_manual_paste(image_path, message, detail)
                return

            status = macos_permission_status()
            if not macos_automatic_paste_ready(status):
                self._copy_for_manual_paste(
                    image_path,
                    message,
                    "macOS is not allowing keyboard events for automatic paste. The annotation was preserved on the clipboard; allow Accessibility for Annota, then try again.",
                    7200,
                )
                macos_request_accessibility()
                self.open_macos_setup()
                return

            if not focus_macos_app(target):
                self._copy_for_manual_paste(
                    image_path,
                    message,
                    "Annota could not focus the selected macOS chat app. The annotation was copied instead of being lost.",
                )
                return

            clipboard = QApplication.clipboard()
            clipboard.setPixmap(QPixmap(image_path))

            def paste_macos_image():
                ok, error = paste_shortcut()
                if not ok:
                    self._copy_for_manual_paste(
                        image_path,
                        message,
                        f"Automatic image paste was blocked: {error}. The annotation was copied for manual paste.",
                        7200,
                    )
                    self.open_macos_setup()
                    return

                def paste_macos_text():
                    clipboard.setText(message)
                    ok_text, text_error = paste_shortcut()
                    if not ok_text:
                        self._show_toast(
                            "Notes copied for manual paste",
                            f"The screenshot paste was requested, but macOS blocked the notes paste: {text_error}. Press Command+V to paste the notes; the image file is saved in Annota's temporary folder.",
                            7600,
                        )
                        self.open_macos_setup()
                        return
                    self._show_toast(
                        "Paste requested in current chat",
                        "Annota posted the screenshot and notes with native macOS paste events. Review the composer before sending. The notes remain on the clipboard as a fallback.",
                        6000,
                    )

                QTimer.singleShot(700, paste_macos_text)

            # Give AppKit time to finish activating the destination before Cmd+V.
            QTimer.singleShot(420, paste_macos_image)
            return

        target = find_chat_window()
        if not target:
            detail = (
                "The annotated image and notes are on the clipboard and saved in %TEMP%\\Annota."
                if route_was_clipboard
                else "No open Codex or ChatGPT window was found. The annotated image and notes are on the clipboard and saved in %TEMP%\\Annota."
            )
            self._copy_for_manual_paste(image_path, message, detail, 5600)
            self.tray.showMessage(
                "Annota", "Annotation copied for manual paste.", QSystemTrayIcon.Warning, 4500
            )
            return
        if not focus_window(target):
            self._copy_for_manual_paste(
                image_path,
                message,
                "Annota could not focus the current chat. The annotated image and notes remain available locally.",
                5600,
            )
            self.tray.showMessage(
                "Annota",
                "Could not focus the current chat. Annotation copied for manual paste.",
                QSystemTrayIcon.Warning,
                4500,
            )
            return

        clipboard = QApplication.clipboard()
        clipboard.setPixmap(QPixmap(image_path))

        def paste_windows_image():
            ok, error = paste_shortcut()
            if not ok:
                self._copy_for_manual_paste(
                    image_path,
                    message,
                    f"Automatic image paste failed: {error}. The annotation was copied for manual paste.",
                )
                return

            def paste_windows_text():
                clipboard.setText(message)
                ok_text, text_error = paste_shortcut()
                if not ok_text:
                    self._show_toast(
                        "Notes copied for manual paste",
                        f"The image was inserted, but the notes paste failed: {text_error}. Press Ctrl+V to paste the notes.",
                        6200,
                    )
                    return
                self._show_toast(
                    "Inserted into current chat",
                    "Screenshot and notes are ready. Review them in the composer, then send when you are satisfied.",
                    4600,
                )
                self.tray.showMessage(
                    "Annota",
                    "Screenshot and notes inserted. Review them before sending.",
                    QSystemTrayIcon.Information,
                    3400,
                )
                if self.settings.value("behavior/clear_after_send", True, type=bool):
                    QTimer.singleShot(3000, lambda: clear_if_current(message))

            QTimer.singleShot(650, paste_windows_text)

        QTimer.singleShot(240, paste_windows_image)

    def open_settings(self):
        if self.settings_dialog and self.settings_dialog.isVisible():
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
            return
        self.settings_dialog = SettingsDialog(self.settings)
        self.settings_dialog.shortcutChanged.connect(self._update_hotkey)
        self.settings_dialog.pauseChanged.connect(self._set_pause_from_settings)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def _update_hotkey(self, sequence: str):
        self._update_annotate_action()
        if not self.pause_action.isChecked():
            self.hotkey.set_sequence(sequence)
        if is_macos():
            QTimer.singleShot(500, self._refresh_macos_hotkey_status)
            self._show_toast(
                "Quick Capture shortcut updated", f"Quick Capture is now set to {sequence}.", 3200
            )
        else:
            self.tray.showMessage(
                "Annota",
                f"Quick Annotate shortcut set to {sequence}.",
                QSystemTrayIcon.Information,
                2500,
            )

    def _set_pause_from_settings(self, paused: bool):
        self.pause_action.setChecked(paused)

    def _pause_hotkey(self, paused: bool):
        self.settings.setValue("behavior/pause_shortcut", paused)
        if paused:
            self.hotkey.stop()
        else:
            self.hotkey.set_sequence(self.settings.value("shortcut", default_shortcut()))
        if is_macos():
            QTimer.singleShot(300, self._refresh_macos_hotkey_status)

    def show_about(self):
        QMessageBox.information(
            None,
            "About Annota",
            f"Annota {APP_VERSION}\n\nQuick desktop annotation for visual development feedback.\n\nDefault shortcut: {default_shortcut()}\n\nNo telemetry. No account. Local-first.",
        )

    def quit(self):
        self.hotkey.stop()
        self._annota_command_timer.stop()
        if self._mac_status_timer is not None:
            self._mac_status_timer.stop()
        self.tray.hide()
        _close_instance_socket()
        self.app.quit()


def default_shortcut() -> str:
    return "Option+Q" if platform.system() == "Darwin" else "Alt+Q"


def tray_click_starts_annotation(reason) -> bool:
    """Return whether a tray activation should immediately start capture.

    macOS menu-bar clicks must remain available for opening the context menu;
    capture is started from the explicit Annotate Now action or Quick Capture.
    """
    return not is_macos() and reason == QSystemTrayIcon.Trigger


def normalize_shortcut(text: str) -> str:
    text = text.replace(" ", "")
    if not text:
        return ""
    parts = text.split("+")
    if len(parts) < 2:
        return ""
    mods = []
    key = parts[-1].upper()
    for part in parts[:-1]:
        lowered = part.lower()
        if lowered in ("alt", "option"):
            mods.append("Option" if platform.system() == "Darwin" else "Alt")
        elif lowered in ("ctrl", "control"):
            mods.append("Ctrl")
        elif lowered == "shift":
            mods.append("Shift")
        elif lowered in ("cmd", "command", "meta", "win", "windows"):
            mods.append("Cmd" if platform.system() == "Darwin" else "Win")
        else:
            return ""
    if len(key) != 1 and not (key.startswith("F") and key[1:].isdigit()):
        return ""
    if key.startswith("F") and key[1:].isdigit() and not (1 <= int(key[1:]) <= 24):
        return ""
    return "+".join(mods + [key])


def to_pynput_hotkey(sequence: str) -> str:
    mapping = {
        "alt": "<alt>",
        "option": "<alt>",
        "ctrl": "<ctrl>",
        "shift": "<shift>",
        "cmd": "<cmd>",
        "win": "<cmd>",
    }
    parts = sequence.lower().split("+")
    output = []
    for part in parts[:-1]:
        if part not in mapping:
            return ""
        output.append(mapping[part])
    output.append(parts[-1])
    return "+".join(output)


def macos_hotkey_supported(sequence: str) -> bool:
    normalized = normalize_shortcut(sequence)
    if not normalized:
        return False
    key = normalized.split("+")[-1]
    if len(key) == 1 and key.isalnum():
        return True
    if key.startswith("F") and key[1:].isdigit():
        return 1 <= int(key[1:]) <= 20
    return False


def shortcut_conflicts(sequence: str) -> bool:
    if platform.system() != "Windows":
        return False
    normalized = normalize_shortcut(sequence)
    if not normalized:
        return True
    parts = normalized.split("+")
    key = parts[-1]
    modifier_flags = 0x4000
    for modifier in parts[:-1]:
        if modifier == "Alt":
            modifier_flags |= 0x0001
        elif modifier == "Ctrl":
            modifier_flags |= 0x0002
        elif modifier == "Shift":
            modifier_flags |= 0x0004
        elif modifier == "Win":
            modifier_flags |= 0x0008
    if len(key) == 1:
        virtual_key = ord(key.upper())
    elif key.startswith("F") and key[1:].isdigit():
        number = int(key[1:])
        if not 1 <= number <= 24:
            return True
        virtual_key = 112 + number - 1
    else:
        return True
    hotkey_id = 41242
    try:
        user32 = ctypes.windll.user32
        registered = bool(user32.RegisterHotKey(None, hotkey_id, modifier_flags, virtual_key))
        if registered:
            user32.UnregisterHotKey(None, hotkey_id)
            return False
        return True
    except Exception:
        return False


def active_window_context() -> tuple[str, str]:
    if is_macos():
        target = macos_frontmost_app()
        return target.get("name", "macOS"), "Active macOS app"
    if platform.system() != "Windows":
        return platform.system(), "Active desktop window"
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        title_buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buffer, length + 1)
        title = title_buffer.value or "Unknown window"
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process_name = f"PID {pid.value}"
        handle = kernel32.OpenProcess(4096, False, pid.value)
        if handle:
            try:
                size = ctypes.c_ulong(32768)
                path_buffer = ctypes.create_unicode_buffer(size.value)
                if kernel32.QueryFullProcessImageNameW(handle, 0, path_buffer, ctypes.byref(size)):
                    process_name = Path(path_buffer.value).name
            finally:
                kernel32.CloseHandle(handle)
        return process_name, title
    except Exception:
        return "Windows", "Unknown window"


BROWSER_EXECUTABLES = {
    "chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "brave.exe",
    "opera.exe",
    "opera_gx.exe",
    "vivaldi.exe",
    "arc.exe",
}
ROUTE_PRIORITY = ("codex", "chatgpt_desktop", "chatgpt_web")
_SEND_ROUTE_OVERRIDE: str | None = None
_PENDING_SEND_ROUTE: str | None = None


def classify_chat_window(title: str, executable: str = "") -> str | None:
    title_l = (title or "").strip().lower()
    exe_l = (executable or "").strip().lower()
    exe_name = exe_l.replace("\\", "/").rsplit("/", 1)[-1]
    is_browser = exe_name in BROWSER_EXECUTABLES
    is_chatgpt_desktop = "chatgpt" in exe_l and not is_browser
    is_codex_process = "codex" in exe_l and not is_browser
    if is_codex_process:
        return "codex"
    if is_chatgpt_desktop and "codex" in title_l:
        return "codex"
    if "codex" in title_l and not is_browser:
        return "codex"
    if is_chatgpt_desktop:
        return "chatgpt_desktop"
    if is_browser and ("chatgpt" in title_l or "chatgpt.com" in title_l):
        return "chatgpt_web"
    if "chatgpt" in title_l and not is_browser:
        return "chatgpt_desktop"
    return None


def choose_chat_target(targets: list[dict], route: str | None = None) -> int | None:
    if route == "clipboard":
        return None
    wanted = ROUTE_PRIORITY if not route or route == "auto" else (route,)
    for route_name in wanted:
        for target in targets:
            if target.get("route") == route_name:
                hwnd = target.get("hwnd")
                if isinstance(hwnd, int) and hwnd:
                    return hwnd
    return None


def _process_image_path(pid: int) -> str:
    if os.name != "nt" or not pid:
        return ""
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        query = kernel32.QueryFullProcessImageNameW
        query.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        query.restype = wintypes.BOOL
        return buffer.value if query(handle, 0, buffer, ctypes.byref(size)) else ""
    finally:
        kernel32.CloseHandle(handle)


def detect_chat_targets() -> list[dict]:
    if os.name != "nt":
        return []
    user32 = ctypes.windll.user32
    own_pid = os.getpid()
    found = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if not title or title.lower().startswith("annota"):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == own_pid:
            return True
        executable = _process_image_path(pid.value)
        route = classify_chat_window(title, executable)
        if route:
            found.append(
                {
                    "hwnd": int(hwnd),
                    "title": title,
                    "pid": int(pid.value),
                    "executable": executable,
                    "route": route,
                }
            )
        return True

    callback_ref = EnumWindowsProc(callback)
    user32.EnumWindows(callback_ref, 0)
    return found


def find_chat_window() -> int | None:
    return choose_chat_target(detect_chat_targets(), _SEND_ROUTE_OVERRIDE)


def focus_window(hwnd: int) -> bool:
    if platform.system() != "Windows" or not hwnd:
        return False
    try:
        user32 = ctypes.windll.user32
        user32.ShowWindow(hwnd, 9)
        return bool(user32.SetForegroundWindow(hwnd))
    except Exception:
        return False


def paste_shortcut() -> tuple[bool, str]:
    if is_macos():
        return macos_post_paste_shortcut()
    if keyboard is None:
        return False, "Keyboard backend unavailable"
    try:
        controller = keyboard.Controller()
        with controller.pressed(keyboard.Key.ctrl):
            controller.press("v")
            controller.release("v")
        return True, ""
    except Exception as exc:
        return False, f"Paste shortcut failed: {exc}"


def clipboard_fallback(image_path: str, message: str):
    clipboard = QApplication.clipboard()
    mime = QMimeData()
    mime.setText(message)
    image = QPixmap(image_path).toImage()
    mime.setImageData(image)
    clipboard.setMimeData(mime)
    Path(image_path).with_suffix(".txt").write_text(message, encoding="utf-8")


def clear_if_current(text: str):
    clipboard = QApplication.clipboard()
    if clipboard.text() == text:
        clipboard.clear()


def configure_startup(enabled: bool):
    if is_macos():
        configure_macos_startup(enabled)
        return
    if platform.system() != "Windows" or winreg is None:
        return
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                executable = str(Path(sys.executable).resolve())
                command = (
                    f'"{executable}"'
                    if getattr(sys, "frozen", False)
                    else f'"{executable}" "{Path(__file__).resolve()}"'
                )
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
            else:
                with suppress(FileNotFoundError):
                    winreg.DeleteValue(key, APP_NAME)
    except Exception:
        return


def shell_command_for_executable(executable: str | Path) -> str:
    return f'"{Path(executable)}" --annotate'


def _shell_registry_paths() -> tuple[str, ...]:
    return (
        rf"Software\Classes\DesktopBackground\Shell\{SHELL_VERB_NAME}",
        rf"Software\Classes\Directory\Background\shell\{SHELL_VERB_NAME}",
    )


def install_shell_context_menu(executable: str | Path | None = None) -> bool:
    if os.name != "nt" or winreg is None:
        return False
    if executable is None:
        if not getattr(sys, "frozen", False):
            return False
        executable = sys.executable
    exe = str(Path(executable).resolve())
    command = shell_command_for_executable(exe)
    try:
        for base_path in _shell_registry_paths():
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base_path) as key:
                winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "Annota")
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, exe)
                winreg.SetValueEx(key, "Position", 0, winreg.REG_SZ, "Top")
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base_path + r"\command") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
        return True
    except OSError:
        return False


_COMMAND_QUEUE: queue.Queue[str] = queue.Queue()
_INSTANCE_SOCKET: socket.socket | None = None
_INSTANCE_THREAD: threading.Thread | None = None
_INITIAL_QUICK_ANNOTATE = any(arg.lower() in QUICK_ANNOTATE_FLAGS for arg in sys.argv[1:])


def _instance_listener(sock: socket.socket):
    while True:
        try:
            data, _addr = sock.recvfrom(128)
        except OSError:
            return
        command = data.decode("utf-8", errors="ignore").strip().lower()
        if command:
            _COMMAND_QUEUE.put(command)


def _start_or_forward_instance() -> bool:
    global _INSTANCE_SOCKET, _INSTANCE_THREAD
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((INSTANCE_HOST, INSTANCE_PORT))
    except OSError:
        sock.close()
        command = b"annotate" if _INITIAL_QUICK_ANNOTATE else b"show"
        try:
            sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sender.sendto(command, (INSTANCE_HOST, INSTANCE_PORT))
            sender.close()
        except OSError:
            pass
        return False
    _INSTANCE_SOCKET = sock
    _INSTANCE_THREAD = threading.Thread(target=_instance_listener, args=(sock,), daemon=True)
    _INSTANCE_THREAD.start()
    return True


def _drain_instance_commands(app):
    while True:
        try:
            command = _COMMAND_QUEUE.get_nowait()
        except queue.Empty:
            return
        if command == "annotate":
            app.activate_annotation(force=True)
        elif command == "show":
            if is_macos():
                app.open_macos_setup()
            else:
                app.open_settings()


def _close_instance_socket():
    global _INSTANCE_SOCKET
    if _INSTANCE_SOCKET is not None:
        with suppress(OSError):
            _INSTANCE_SOCKET.close()
        _INSTANCE_SOCKET = None


def _find_layout_containing(layout, widget):
    if layout is None:
        return None
    try:
        count = layout.count()
    except Exception:
        return None
    for index in range(count):
        item = layout.itemAt(index)
        if item.widget() is widget:
            return layout
        child_layout = item.layout()
        if child_layout is not None:
            result = _find_layout_containing(child_layout, widget)
            if result is not None:
                return result
    return None


def _send_button_label(route: str | None = None) -> str:
    labels = {
        None: "Auto Send",
        "auto": "Auto Send",
        "codex": "Send to Codex",
        "chatgpt_desktop": "Send to ChatGPT",
        "chatgpt_web": "Send to ChatGPT Web",
        "clipboard": "Copy for Manual Paste",
    }
    return labels.get(route, "Auto Send")


def _apply_pending_send_route(*_args):
    global _SEND_ROUTE_OVERRIDE
    _SEND_ROUTE_OVERRIDE = _PENDING_SEND_ROUTE


def _clear_pending_send_route(*_args):
    global _SEND_ROUTE_OVERRIDE, _PENDING_SEND_ROUTE
    _SEND_ROUTE_OVERRIDE = None
    _PENDING_SEND_ROUTE = None


def _set_pending_send_route(route: str | None, send_button: QPushButton):
    global _PENDING_SEND_ROUTE
    _PENDING_SEND_ROUTE = None if route in (None, "auto") else route
    send_button.setText(_send_button_label(_PENDING_SEND_ROUTE))
    if _PENDING_SEND_ROUTE is None:
        send_button.setToolTip(
            "Auto Send: Codex first, then ChatGPT desktop, ChatGPT web, then clipboard fallback"
        )
    else:
        send_button.setToolTip(f"Use {_send_button_label(_PENDING_SEND_ROUTE)} after Review")


def _add_send_route_menu(root, send_button: QPushButton | None = None):
    if root.property("annotaRouteMenuAdded"):
        return
    if send_button is None:
        buttons = root.findChildren(QPushButton)
        send_button = next(
            (
                button
                for button in buttons
                if button.objectName() in {"sendButton", "toolbarPrimary"}
                or button.text().strip() in {"Auto Send", "Send", "Send to Codex"}
            ),
            None,
        )
    if send_button is None:
        return

    _set_pending_send_route(_PENDING_SEND_ROUTE, send_button)
    parent = send_button.parentWidget()
    layout = _find_layout_containing(parent.layout() if parent else None, send_button)
    if layout is None:
        layout = _find_layout_containing(root.layout(), send_button)
    if layout is None:
        return

    route_button = QToolButton(parent or root)
    route_button.setObjectName("sendRouteButton")
    route_button.setText(chr(0x25BE))
    route_button.setToolTip("Choose Auto Send or a specific destination")
    route_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    menu = QMenu(route_button)

    auto_action = menu.addAction("Auto Send (Recommended)")
    auto_action.triggered.connect(
        lambda _checked=False, b=send_button: _set_pending_send_route(None, b)
    )
    menu.addSeparator()
    for label, route in (
        ("Send to Codex", "codex"),
        ("Send to ChatGPT desktop", "chatgpt_desktop"),
        ("Send to ChatGPT web", "chatgpt_web"),
    ):
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
    layout.insertWidget(layout.indexOf(send_button) + 1, route_button)
    root.setProperty("annotaRouteMenuAdded", True)
    root._annota_route_button = route_button


def _runtime_self_test() -> int:
    result = {
        "platform": platform.system(),
        "version": APP_VERSION,
        "icon_exists": ICON_PATH.exists(),
        "send_icon_exists": SEND_ICON_PATH.exists(),
        "keyboard_backend": keyboard is not None,
    }
    if is_macos():
        result["native_hotkey_helper"] = HOTKEY_HELPER_PATH.exists() and os.access(
            HOTKEY_HELPER_PATH, os.X_OK
        )
        result["permissions"] = macos_permission_status()
        result["automatic_paste_ready"] = macos_automatic_paste_ready(result["permissions"])
        try:
            import AppKit  # noqa: F401
            import HIServices  # noqa: F401
            import Quartz  # noqa: F401

            result["mac_frameworks"] = True
        except Exception:
            result["mac_frameworks"] = False
    print(json.dumps(result, sort_keys=True))
    ok = result["icon_exists"] and result["send_icon_exists"] and result["keyboard_backend"]
    if is_macos():
        ok = (
            ok and result.get("mac_frameworks", False) and result.get("native_hotkey_helper", False)
        )
    return 0 if ok else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return _runtime_self_test()
    smoke_test = "--smoke-test" in sys.argv
    if smoke_test:
        os.environ["ANNOTA_CI_SMOKE"] = "1"
    if not _start_or_forward_instance():
        return 0
    install_shell_context_menu()
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    controller = AnnotaApp(app)
    app._annota_controller = controller
    if smoke_test:
        QTimer.singleShot(1800, controller.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
