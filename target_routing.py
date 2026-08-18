"""Supported Auto Send targets and deterministic target selection for Annota."""

from __future__ import annotations

from collections.abc import Iterable

SUPPORTED_TARGETS = (
    ("codex", "Codex"),
    ("chatgpt", "ChatGPT"),
    ("claude", "Claude"),
    ("cursor", "Cursor"),
    ("vscode", "Visual Studio Code"),
    ("windsurf", "Windsurf"),
    ("opencode", "OpenCode"),
)
TARGET_ORDER = tuple(route for route, _label in SUPPORTED_TARGETS)
TARGET_LABELS = dict(SUPPORTED_TARGETS)

_BROWSER_EXECUTABLES = {"arc.exe", "brave.exe", "chrome.exe", "firefox.exe", "msedge.exe", "opera.exe", "opera_gx.exe", "vivaldi.exe"}

_WINDOWS_EXECUTABLES = {
    "codex": {"codex.exe", "codex-app.exe"},
    "chatgpt": {"chatgpt.exe"},
    "claude": {"claude.exe"},
    "cursor": {"cursor.exe"},
    "vscode": {"code.exe", "code-insiders.exe", "vscode.exe"},
    "windsurf": {"windsurf.exe"},
    "opencode": {"opencode.exe", "opencode-desktop.exe"},
}

_MAC_TOKENS = {
    "codex": ("codex", "com.openai.codex"),
    "chatgpt": ("chatgpt", "com.openai.chat"),
    "claude": ("claude", "com.anthropic.claude"),
    "cursor": ("cursor", "com.todesktop.230313mzl4w4u92"),
    "vscode": ("visual studio code", "com.microsoft.vscode"),
    "windsurf": ("windsurf", "com.codeium.windsurf"),
    "opencode": ("opencode",),
}


def is_auto_route(route: str | None) -> bool:
    return route in (None, "auto")


def target_label(route: str | None) -> str:
    if is_auto_route(route):
        return "Auto Send"
    if route == "clipboard":
        return "Copy for Manual Paste"
    return "Send"


def target_description(route: str | None) -> str:
    if is_auto_route(route):
        return "Automatically send to the app active when annotation started."
    if route == "clipboard":
        return "Copy annotation for manual paste."
    return f"Send only to {TARGET_LABELS.get(route, route)}."


def classify_windows_target(title: str, executable: str = "") -> str | None:
    title_l = (title or "").strip().lower()
    exe_name = (executable or "").strip().lower().replace("\\", "/").rsplit("/", 1)[-1]
    if exe_name in _BROWSER_EXECUTABLES:
        return None
    for route in TARGET_ORDER:
        if exe_name in _WINDOWS_EXECUTABLES[route]:
            return route
    for token, route in (("codex", "codex"), ("chatgpt", "chatgpt"), ("claude", "claude"), ("cursor", "cursor"), ("vscode", "vscode"), ("visual studio code", "vscode"), ("windsurf", "windsurf"), ("opencode", "opencode")):
        if token in title_l:
            return route
    return None


def classify_macos_target(target: dict) -> str | None:
    value = f"{target.get('name', '')} {target.get('bundle_id', '')}".lower()
    for route, tokens in _MAC_TOKENS.items():
        if any(token in value for token in tokens):
            return route
    return None


def _same_target(left: dict, right: dict) -> bool:
    return any(left.get(key) and left.get(key) == right.get(key) for key in ("hwnd", "pid"))


def choose_target_record(targets: Iterable[dict], route: str | None = None, source_target: dict | None = None) -> dict | None:
    """Choose a destination. Manual selections are locked; auto uses capture source first."""
    if route == "clipboard":
        return None
    candidates = [dict(item) for item in targets if item.get("route") in TARGET_ORDER]
    if not is_auto_route(route):
        return next((item for item in candidates if item.get("route") == route), None)
    source = dict(source_target or {})
    for item in candidates:
        if item.get("route") == source.get("route") and _same_target(item, source):
            return item
    for wanted in TARGET_ORDER:
        if match := next((item for item in candidates if item.get("route") == wanted), None):
            return match
    return None
