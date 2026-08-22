from target_routing import (
    TARGET_ORDER,
    choose_target_record,
    classify_macos_target,
    classify_windows_target,
    target_description,
    target_label,
)


def test_supported_target_order_is_exact():
    assert TARGET_ORDER == (
        "codex",
        "chatgpt",
        "claude",
        "cursor",
        "vscode",
        "windsurf",
        "opencode",
        "cline",
        "roo_code",
        "github_copilot",
        "gemini",
    )


def test_route_labels_and_descriptions_match_send_mode():
    assert target_label(None) == "Auto Send"
    assert target_label("auto") == "Auto Send"
    assert (
        target_description(None) == "Automatically send to the app active when annotation started."
    )

    for route, label in (
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
    ):
        assert target_label(route) == "Send"
        assert target_description(route) == f"Send only to {label}."

    assert target_label("clipboard") == "Copy for Manual Paste"
    assert target_description("clipboard") == "Copy annotation for manual paste."


def test_windows_classification_supports_all_apps_and_chatgpt_web():
    cases = {
        r"C:\\Apps\\Codex.exe": "codex",
        r"C:\\Apps\\ChatGPT.exe": "chatgpt",
        r"C:\\Apps\\Claude.exe": "claude",
        r"C:\\Apps\\Cursor.exe": "cursor",
        r"C:\\Apps\\Code.exe": "vscode",
        r"C:\\Apps\\Windsurf.exe": "windsurf",
        r"C:\\Apps\\OpenCode.exe": "opencode",
        r"C:\\Apps\\Cline.exe": "cline",
        r"C:\\Apps\\Roo-Code.exe": "roo_code",
        r"C:\\Apps\\GitHub-Copilot.exe": "github_copilot",
        r"C:\\Apps\\Gemini.exe": "gemini",
    }
    for executable, expected in cases.items():
        assert classify_windows_target("Project", executable) == expected

    for executable in (
        r"C:\\Chrome\\chrome.exe",
        r"C:\\Firefox\\firefox.exe",
        r"C:\\Edge\\msedge.exe",
    ):
        assert classify_windows_target("ChatGPT - browser", executable) == "chatgpt"
        assert classify_windows_target("chatgpt.com - browser", executable) == "chatgpt"
        assert classify_windows_target("GitHub - browser", executable) is None


def test_editor_extension_titles_win_over_vscode_host():
    code = r"C:\\Apps\\Code.exe"
    assert classify_windows_target("Cline - Visual Studio Code", code) == "cline"
    assert classify_windows_target("Roo Code - Visual Studio Code", code) == "roo_code"
    assert classify_windows_target("GitHub Copilot - Visual Studio Code", code) == "github_copilot"
    assert classify_windows_target("Gemini - Visual Studio Code", code) == "gemini"


def test_browser_classification_supports_gemini_and_github_copilot():
    chrome = r"C:\\Chrome\\chrome.exe"
    assert classify_windows_target("Gemini", chrome) == "gemini"
    assert classify_windows_target("gemini.google.com - Google Chrome", chrome) == "gemini"
    assert classify_windows_target("GitHub Copilot - Google Chrome", chrome) == "github_copilot"
    assert classify_windows_target("GitHub - Google Chrome", chrome) is None


def test_macos_classification_supports_all_apps():
    assert classify_macos_target({"name": "Codex", "bundle_id": "com.openai.codex"}) == "codex"
    assert classify_macos_target({"name": "ChatGPT", "bundle_id": "com.openai.chat"}) == "chatgpt"
    assert (
        classify_macos_target({"name": "Claude", "bundle_id": "com.anthropic.claude"}) == "claude"
    )
    assert (
        classify_macos_target({"name": "Cursor", "bundle_id": "com.todesktop.230313mzl4w4u92"})
        == "cursor"
    )
    assert (
        classify_macos_target({"name": "Visual Studio Code", "bundle_id": "com.microsoft.VSCode"})
        == "vscode"
    )
    assert (
        classify_macos_target({"name": "Windsurf", "bundle_id": "com.codeium.windsurf"})
        == "windsurf"
    )
    assert (
        classify_macos_target({"name": "OpenCode", "bundle_id": "ai.opencode.desktop"})
        == "opencode"
    )


def test_auto_send_prefers_app_active_when_capture_started():
    source = {"hwnd": 22, "pid": 222, "route": "cursor"}
    targets = [
        {"hwnd": 11, "pid": 111, "route": "codex"},
        {"hwnd": 22, "pid": 222, "route": "cursor"},
    ]
    assert choose_target_record(targets, None, source)["hwnd"] == 22


def test_auto_send_prefers_active_chatgpt_web_over_other_supported_apps():
    source = {"hwnd": 44, "pid": 444, "route": "chatgpt"}
    targets = [
        {"hwnd": 11, "pid": 111, "route": "codex"},
        {"hwnd": 44, "pid": 444, "route": "chatgpt"},
    ]
    selected = choose_target_record(targets, None, source)
    assert selected["route"] == "chatgpt"
    assert selected["hwnd"] == 44


def test_auto_send_keeps_source_app_when_its_window_is_recreated():
    source = {"hwnd": 22, "pid": 222, "route": "opencode"}
    targets = [
        {"hwnd": 11, "pid": 111, "route": "codex"},
        {"hwnd": 77, "pid": 777, "route": "opencode"},
    ]
    selected = choose_target_record(targets, None, source)
    assert selected["route"] == "opencode"
    assert selected["hwnd"] == 77


def test_manual_extension_route_can_use_generic_vscode_host():
    targets = [{"hwnd": 55, "pid": 555, "route": "vscode"}]
    for route in ("cline", "roo_code", "github_copilot", "gemini"):
        selected = choose_target_record(targets, route, None)
        assert selected is not None
        assert selected["hwnd"] == 55


def test_cline_manual_route_can_use_cursor_or_windsurf_host():
    cursor = [{"hwnd": 66, "pid": 666, "route": "cursor"}]
    windsurf = [{"hwnd": 77, "pid": 777, "route": "windsurf"}]
    assert choose_target_record(cursor, "cline", None)["hwnd"] == 66
    assert choose_target_record(windsurf, "cline", None)["hwnd"] == 77


def test_auto_send_falls_back_to_stable_priority_when_source_is_not_supported():
    targets = [
        {"hwnd": 33, "pid": 333, "route": "claude"},
        {"hwnd": 11, "pid": 111, "route": "codex"},
    ]
    assert (
        choose_target_record(targets, None, {"hwnd": 99, "pid": 999, "route": None})["route"]
        == "codex"
    )


def test_manual_route_only_uses_selected_supported_app_and_ignores_active_source():
    targets = [
        {"hwnd": 11, "pid": 111, "route": "codex"},
        {"hwnd": 77, "pid": 777, "route": "opencode"},
    ]
    active_codex = {"hwnd": 11, "pid": 111, "route": "codex"}

    selected = choose_target_record(targets, "opencode", active_codex)

    assert selected["hwnd"] == 77
    assert selected["route"] == "opencode"
    assert choose_target_record(targets, "windsurf", active_codex) is None
    assert choose_target_record(targets, "clipboard", active_codex) is None
