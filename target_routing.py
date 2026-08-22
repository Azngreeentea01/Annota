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
    ("cline", "Cline"),
    ("roo_code", "Roo Code"),
    ("github_copilot", "GitHub Copilot"),
    ("gemini", "Gemini"),
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
    "cline": {"cline.exe"},
    "roo_code": {"roo-code.exe", "roocode.exe"},
    "github_copilot": {"github-copilot.exe", "copilot.exe"},
    "gemini": {"gemini.exe"},
}

_MAC_TOKENS = {
    "codex": ("codex", "com.openai.codex"),
    "chatgpt": ("chatgpt", "com.openai.chat"),
    "claude": ("claude", "com.anthropic.claude"),
    "cursor": ("cursor", "com.todesktop.230313mzl4w4u92"),
    "vscode": ("visual studio code", "com.microsoft.vscode"),
    "windsurf": ("windsurf", "com.codeium.windsurf"),
    "opencode": ("opencode",),
    "cline": ("cline",),
    "roo_code": ("roo code", "roo-code", "roocode"),
    "github_copilot": ("github copilot", "github.copilot"),
    "gemini": ("gemini", "com.google.gemini"),
}

_TITLE_ROUTES = (
    ("github copilot", "github_copilot"),
    ("roo code", "roo_code"),
    ("roo-code", "roo_code"),
    ("roocode", "roo_code"),
    ("opencode", "opencode"),
    ("cline", "cline"),
    ("gemini", "gemini"),
    ("visual studio code", "vscode"),
    ("windsurf", "windsurf"),
    ("chatgpt", "chatgpt"),
    ("claude", "claude"),
    ("cursor", "cursor"),
    ("codex", "codex"),
)

_BROWSER_TITLE_ROUTES = (
    ("chatgpt.com", "chatgpt"),
    ("chatgpt", "chatgpt"),
    ("claude.ai", "claude"),
    ("claude", "claude"),
    ("gemini.google.com", "gemini"),
    ("gemini", "gemini"),
    ("github copilot", "github_copilot"),
    ("copilot - github", "github_copilot"),
)

_MANUAL_HOST_FALLBACKS = {
    "cline": ("vscode", "cursor", "windsurf"),
    "roo_code": ("vscode",),
    "github_copilot": ("vscode",),
    "gemini": ("vscode",),
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
    """Classify a supported Windows destination from its process and window title.

    Browser destinations are classified from their top-level title. Editor
    extensions such as Cline, Roo Code, and GitHub Copilot are also classified
    by title before the host executable so they are not mistaken for plain VS Code.
    """
    title_l = (title or "").strip().lower()
    exe_name = (executable or "").strip().lower().replace("\\", "/").rsplit("/", 1)[-1]

    if exe_name in _BROWSER_EXECUTABLES:
        for token, route in _BROWSER_TITLE_ROUTES:
            if token in title_l:
                return route
        return None

    # Extension/product titles must win over generic host executables such as Code.exe.
    for token, route in _TITLE_ROUTES:
        if token in title_l:
            return route

    for route in TARGET_ORDER:
        if exe_name in _WINDOWS_EXECUTABLES[route]:
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


def choose_target_record(
    targets: Iterable[dict], route: str | None = None, source_target: dict | None = None
) -> dict | None:
    """Choose a destination. Manual selections are locked; auto uses capture source first.

    Auto mode first tries the exact source window/process. If that window was
    recreated (common with Electron apps), it next prefers another live window
    for the same supported app before falling back to the stable global order.
    """
    if route == "clipboard":
        return None
    candidates = [dict(item) for item in targets if item.get("route") in TARGET_ORDER]
    if not is_auto_route(route):
        if match := next((item for item in candidates if item.get("route") == route), None):
            return match
        for host_route in _MANUAL_HOST_FALLBACKS.get(route, ()):
            if match := next((item for item in candidates if item.get("route") == host_route), None):
                return match
        return None

    source = dict(source_target or {})
    source_route = source.get("route")
    if source_route in TARGET_ORDER:
        for item in candidates:
            if item.get("route") == source_route and _same_target(item, source):
                return item
        if match := next((item for item in candidates if item.get("route") == source_route), None):
            return match

    for wanted in TARGET_ORDER:
        if match := next((item for item in candidates if item.get("route") == wanted), None):
            return match
    return None
