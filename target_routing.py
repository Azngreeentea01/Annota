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

_BROWSER_EXECUTABLES = {
    "arc.exe",
    "brave.exe",
    "chrome.exe",
    "firefox.exe",
    "msedge.exe",
    "opera.exe",
    "opera_gx.exe",
    "vivaldi.exe",
}

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


def target_label(route: str | None) -> str:
    if route in (None, "auto"):
        return "Auto Send"
    if route == "clipboard":
        return "Copy for Manual Paste"
    label = TARGET_LABELS.get(route)
    return f"Send to {label}" if label else "Auto Send"


def classify_windows_target(title: str, executable: str = "") -> str | None:
    """Classify a visible Windows app without treating browser tabs as targets."""
    title_l = (title or "").strip().lower()
    executable_l = (executable or "").strip().lower().replace("\\", "/")
    exe_name = executable_l.rsplit("/", 1)[-1]
    if exe_name in _BROWSER_EXECUTABLES:
        return None
    for route in TARGET_ORDER:
        if exe_name in _WINDOWS_EXECUTABLES[route]:
            return route

    # Conservative title fallbacks help when Windows blocks process-path lookup.
    title_tokens = (
        ("codex", "codex"),
        ("chatgpt", "chatgpt"),
        ("claude", "claude"),
        ("cursor", "cursor"),
        ("vscode", "visual studio code"),
        ("windsurf", "windsurf"),
        ("opencode", "opencode"),
    )
    for route, token in title_tokens:
        if token in title_l:
            return route
    return None


def classify_macos_target(target: dict) -> str | None:
    value = f"{target.get('name', '')} {target.get('bundle_id', '')}".lower()
    for route in TARGET_ORDER:
        if any(token in value for token in _MAC_TOKENS[route]):
            return route
    return None


def _same_target(left: dict, right: dict) -> bool:
    for key in ("hwnd", "pid"):
        a = left.get(key)
        b = right.get(key)
        if a and b and a == b:
            return True
    return False


def choose_target_record(
    targets: Iterable[dict], route: str | None = None, source_target: dict | None = None
) -> dict | None:
    """Prefer the supported app active when capture began, then stable app priority."""
    if route == "clipboard":
        return None
    candidates = [dict(target) for target in targets if target.get("route") in TARGET_ORDER]
    wanted = TARGET_ORDER if route in (None, "auto") else (route,)
    source = dict(source_target or {})
    source_route = source.get("route")
    if source_route in wanted:
        for candidate in candidates:
            if candidate.get("route") == source_route and _same_target(candidate, source):
                return candidate
    for wanted_route in wanted:
        for candidate in candidates:
            if candidate.get("route") == wanted_route:
                return candidate
    return None
