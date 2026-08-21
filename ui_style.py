"""Platform-aware visual styling for Annota.

The existing lavender identity remains the base theme. Windows receives a
small Fluent-inspired override layer so the application feels native beside
modern Windows 11 apps without changing widget behavior or the macOS look.
"""

from __future__ import annotations

import platform


WINDOWS11_STYLE = r"""
/* Windows 11 / Fluent-inspired visual layer */
QWidget {
    font-family: 'Segoe UI Variable Text', 'Segoe UI';
    font-size: 10pt;
    color: #242124;
}

QDialog {
    background: #F8F7FB;
}

#noteCard, #reviewCard, #statusToast {
    background: #FCFCFD;
    border: 1px solid #DCD8E5;
    border-radius: 14px;
}

#reviewCard {
    background: #FAF9FC;
}

#previewCard, #notesCard, #settingsCard {
    background: #FFFFFF;
    border: 1px solid #E1DEE7;
    border-radius: 10px;
}

#previewImage {
    background: #F5F3F9;
    border: 1px solid #ECE9F1;
    border-radius: 8px;
    padding: 4px;
}

#modePill {
    background: #7650E8;
    color: #FFFFFF;
    border: 1px solid #6843D8;
    border-radius: 14px;
    padding: 8px 15px;
    font-size: 10pt;
    font-weight: 600;
}

#noteTitle, #toastTitle {
    color: #242124;
    font-weight: 600;
}

#reviewTitle {
    color: #242124;
    font-size: 17pt;
    font-weight: 650;
}

#dialogTitle {
    color: #242124;
    font-size: 20pt;
    font-weight: 650;
}

#sectionTitle {
    color: #6040C5;
    font-size: 11pt;
    font-weight: 600;
}

#hint, #muted, #toastDetail {
    color: #68636F;
    font-size: 9.5pt;
}

#noteMarker, #toastBadge {
    background: #7650E8;
    color: #FFFFFF;
    border: none;
    border-radius: 14px;
    font-weight: 650;
}

QTextEdit, QLineEdit, QSpinBox {
    background: #FFFFFF;
    color: #242124;
    border: 1px solid #CFCBD5;
    border-radius: 6px;
    padding: 8px 10px;
    selection-background-color: #CFC2FF;
    selection-color: #242124;
}

QTextEdit:hover, QLineEdit:hover, QSpinBox:hover {
    border-color: #BDB8C5;
}

QTextEdit:focus, QLineEdit:focus, QSpinBox:focus {
    border: 2px solid #7650E8;
    padding: 7px 9px;
}

#primaryButton, #sendButton, #toolbarPrimary {
    background: #7650E8;
    color: #FFFFFF;
    border: 1px solid #6843D8;
    border-radius: 7px;
    padding: 7px 14px;
    min-height: 20px;
    font-size: 10pt;
    font-weight: 600;
}

#primaryButton:hover, #sendButton:hover, #toolbarPrimary:hover {
    background: #6D49DB;
    border-color: #6040C5;
}

#primaryButton:pressed, #sendButton:pressed, #toolbarPrimary:pressed {
    background: #6040C5;
    border-color: #5637B3;
}

#primaryButton:disabled, #sendButton:disabled, #toolbarPrimary:disabled {
    background: #D8D4E2;
    color: #8A8591;
    border-color: #D0CCD8;
}

#secondaryButton, #toolbarButton, #iconButton {
    background: #FBFAFC;
    color: #242124;
    border: 1px solid #D2CED8;
    border-radius: 7px;
    padding: 7px 13px;
    min-height: 20px;
    font-size: 10pt;
    font-weight: 550;
}

#secondaryButton:hover, #iconButton:hover {
    background: #F1EFF5;
    border-color: #C4C0CA;
}

#secondaryButton:pressed, #iconButton:pressed {
    background: #E7E4EC;
}

#secondaryButton:disabled, #iconButton:disabled {
    background: #F4F2F6;
    color: #9B96A1;
    border-color: #E2DFE6;
}

#toolbar {
    background: rgba(32, 29, 38, 248);
    border: 1px solid rgba(255, 255, 255, 34);
    border-radius: 10px;
}

#toolbarButton {
    background: transparent;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    font-weight: 550;
}

#toolbarButton:hover {
    background: rgba(255, 255, 255, 22);
}

#toolbarButton:pressed {
    background: rgba(255, 255, 255, 34);
}

/* Treat Send + route arrow as a compact Win11 split button. */
#sendButton, #toolbarPrimary {
    border-top-right-radius: 2px;
    border-bottom-right-radius: 2px;
}

#sendRouteButton {
    background: #7650E8;
    color: #FFFFFF;
    border: 1px solid #6843D8;
    border-left-color: #8668EA;
    border-radius: 7px;
    border-top-left-radius: 2px;
    border-bottom-left-radius: 2px;
    padding: 0px;
    min-width: 34px;
    max-width: 34px;
}

/* QToolButton already renders the DownArrow set by the app. Hide the
   platform menu indicator so the split button never displays two arrows. */
#sendRouteButton::menu-indicator {
    image: none;
    width: 0px;
    height: 0px;
}

#sendRouteButton:hover {
    background: #6D49DB;
}

#sendRouteButton:pressed {
    background: #6040C5;
}

#reviewList {
    background: #FFFFFF;
    color: #242124;
    border: 1px solid #DAD6DF;
    border-radius: 7px;
    padding: 4px;
    outline: none;
}

#reviewList::item {
    padding: 9px 8px;
    border: none;
    border-bottom: 1px solid #EFECF2;
}

#reviewList::item:hover {
    background: #F5F2FA;
    border-radius: 5px;
}

#reviewList::item:selected {
    background: #EAE3FF;
    color: #242124;
    border-radius: 5px;
}

QCheckBox {
    spacing: 9px;
    color: #242124;
    font-size: 10pt;
}

QCheckBox:disabled {
    color: #96919C;
}

QMenu {
    background: #FFFFFF;
    color: #242124;
    border: 1px solid #D8D4DE;
    border-radius: 8px;
    padding: 5px;
    font-size: 10pt;
}

QMenu::item {
    padding: 7px 30px 7px 10px;
    border-radius: 5px;
}

QMenu::item:selected {
    background: #F0EDF5;
    color: #242124;
}

QMenu::separator {
    height: 1px;
    background: #E8E5EB;
    margin: 5px 8px;
}

QToolTip {
    background: #25222A;
    color: #FFFFFF;
    border: 1px solid #3A3640;
    border-radius: 5px;
    padding: 5px 7px;
    font-size: 9pt;
}

QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #C8C4CD;
    min-height: 28px;
    border-radius: 4px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background: #AAA5B0;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
    height: 0px;
}
"""


def build_app_style(base_style: str, platform_name: str | None = None) -> str:
    """Return the base theme plus Windows 11 overrides when appropriate."""
    system_name = platform_name or platform.system()
    if system_name.lower() != "windows":
        return base_style
    return f"{base_style.rstrip()}\n\n{WINDOWS11_STYLE.strip()}\n"
