from ui_style import WINDOWS11_STYLE, build_app_style


def test_windows_adds_fluent_visual_layer():
    base = "QWidget { color: black; }"
    styled = build_app_style(base, "Windows")

    assert styled.startswith(base)
    assert "Segoe UI Variable Text" in styled
    assert "#noteCard, #reviewCard, #statusToast" in styled
    assert "#sendRouteButton" in styled
    assert "QMenu::separator" in styled
    assert "QScrollBar::handle:vertical" in styled


def test_non_windows_keeps_base_theme_unchanged():
    base = "QWidget { color: black; }"

    assert build_app_style(base, "Darwin") == base
    assert build_app_style(base, "Linux") == base


def test_windows_style_preserves_lavender_identity_and_split_send_control():
    assert "#7650E8" in WINDOWS11_STYLE
    assert "border-top-right-radius: 2px" in WINDOWS11_STYLE
    assert "border-top-left-radius: 2px" in WINDOWS11_STYLE
    assert "#sendButton, #toolbarPrimary" in WINDOWS11_STYLE


def test_send_route_button_has_one_centered_indicator_and_matching_width():
    assert "min-width: 34px" in WINDOWS11_STYLE
    assert "max-width: 34px" in WINDOWS11_STYLE
    assert "#sendRouteButton::menu-indicator" in WINDOWS11_STYLE
    assert "image: none" in WINDOWS11_STYLE
