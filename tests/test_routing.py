from pathlib import Path

import main


def test_classifies_codex_view_in_chatgpt_desktop():
    assert main.classify_chat_window(
        "Codex - Annota",
        r"C:\Program Files\WindowsApps\OpenAI.ChatGPT\ChatGPT.exe",
    ) == "codex"


def test_classifies_chatgpt_desktop():
    assert main.classify_chat_window(
        "Project chat",
        r"C:\Program Files\WindowsApps\OpenAI.ChatGPT\ChatGPT.exe",
    ) == "chatgpt_desktop"


def test_classifies_chatgpt_web_browser():
    assert main.classify_chat_window(
        "ChatGPT - Google Chrome",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ) == "chatgpt_web"


def test_unrelated_browser_is_not_chat_target():
    assert main.classify_chat_window(
        "Documentation - Google Chrome",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ) is None


def test_auto_route_prioritizes_codex_even_if_listed_last():
    targets = [
        {"hwnd": 101, "route": "chatgpt_web"},
        {"hwnd": 202, "route": "chatgpt_desktop"},
        {"hwnd": 303, "route": "codex"},
    ]
    assert main.choose_chat_target(targets) == 303


def test_route_override_can_choose_web():
    targets = [
        {"hwnd": 303, "route": "codex"},
        {"hwnd": 101, "route": "chatgpt_web"},
    ]
    assert main.choose_chat_target(targets, "chatgpt_web") == 101


def test_clipboard_override_returns_no_window():
    targets = [{"hwnd": 303, "route": "codex"}]
    assert main.choose_chat_target(targets, "clipboard") is None


def test_shell_command_quotes_executable_and_requests_annotation():
    exe = Path(r"C:\Program Files\Annota\Annota.exe")
    assert main.shell_command_for_executable(exe) == '"C:\\Program Files\\Annota\\Annota.exe" --annotate'
