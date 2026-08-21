from pathlib import Path

import main


def test_classifies_codex_app():
    assert (
        main.classify_chat_window(
            "Codex - Annota",
            r"C:\Program Files\Codex\Codex.exe",
        )
        == "codex"
    )


def test_classifies_chatgpt_desktop():
    assert (
        main.classify_chat_window(
            "Project chat",
            r"C:\Program Files\WindowsApps\OpenAI.ChatGPT\ChatGPT.exe",
        )
        == "chatgpt"
    )


def test_browser_tabs_are_not_supported_send_targets():
    assert (
        main.classify_chat_window(
            "ChatGPT - Google Chrome",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        )
        is None
    )


def test_unrelated_browser_is_not_chat_target():
    assert (
        main.classify_chat_window(
            "Documentation - Google Chrome",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        )
        is None
    )


def test_auto_route_prioritizes_codex_when_capture_source_is_not_supported():
    targets = [
        {"hwnd": 202, "route": "chatgpt"},
        {"hwnd": 303, "route": "codex"},
    ]
    assert main.choose_chat_target(targets) == 303


def test_route_override_can_choose_chatgpt():
    targets = [
        {"hwnd": 303, "route": "codex"},
        {"hwnd": 101, "route": "chatgpt"},
    ]
    assert main.choose_chat_target(targets, "chatgpt") == 101


def test_clipboard_override_returns_no_window():
    targets = [{"hwnd": 303, "route": "codex"}]
    assert main.choose_chat_target(targets, "clipboard") is None


def test_shell_command_quotes_executable_and_requests_annotation():
    exe = Path(r"C:\Program Files\Annota\Annota.exe")
    assert (
        main.shell_command_for_executable(exe)
        == '"C:\\Program Files\\Annota\\Annota.exe" --annotate'
    )
