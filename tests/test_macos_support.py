from pathlib import Path

import main


def test_macos_app_classification_contract():
    assert main.classify_macos_app({"name": "Codex", "bundle_id": "com.openai.codex"}) == "codex"
    assert main.classify_macos_app({"name": "ChatGPT", "bundle_id": "com.openai.chat"}) == "chatgpt_desktop"
    assert main.classify_macos_app({"name": "Safari", "bundle_id": "com.apple.Safari"}) == "chatgpt_web"
    assert main.classify_macos_app({"name": "Finder", "bundle_id": "com.apple.finder"}) is None


def test_manual_web_route_can_reuse_source_browser(monkeypatch):
    monkeypatch.setattr(main, "is_macos", lambda: True)
    source = {"pid": 44, "name": "Safari", "bundle_id": "com.apple.Safari"}
    assert main.macos_find_chat_target("chatgpt_web", source) == source


def test_non_macos_permission_status_is_ready():
    status = main.macos_permission_status()
    if not main.is_macos():
        assert status == {"screen_recording": True, "accessibility": True, "post_events": True}


def test_configure_startup_routes_to_macos_helper(monkeypatch):
    called = []
    monkeypatch.setattr(main, "is_macos", lambda: True)
    monkeypatch.setattr(main, "configure_macos_startup", lambda enabled: called.append(enabled))
    main.configure_startup(True)
    assert called == [True]


def test_macos_runtime_reliability_source_contract():
    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "0.2.2"' in source
    assert "self.tray_menu = QMenu()" in source
    assert "CGPreflightScreenCaptureAccess" in source
    assert "AXIsProcessTrusted" in source
    assert "Start Annotation" in source
    assert "--self-test" in source
    assert "--smoke-test" in source
