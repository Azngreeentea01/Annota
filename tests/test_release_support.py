from pathlib import Path

import main

ROOT = Path(__file__).resolve().parents[1]


def test_release_versions_match_application_version():
    expected = main.APP_VERSION
    windows = (ROOT / "release_windows.bat").read_text(encoding="utf-8")
    mac_build = (ROOT / "build_macos.sh").read_text(encoding="utf-8")
    mac_release = (ROOT / "release_macos.sh").read_text(encoding="utf-8")
    mac_kit = (ROOT / "release_macos_kit.bat").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "macos-arm64-build.yml").read_text(
        encoding="utf-8"
    )

    assert f"VERSION={expected}" in windows
    assert f'VERSION="{expected}"' in mac_build
    assert f'VERSION="{expected}"' in mac_release
    assert f"VERSION={expected}" in mac_kit
    assert f'ANNOTA_VERSION: "{expected}"' in workflow


def test_windows_build_quality_gate_contract():
    for filename in ("build.bat", "build_onefile.bat"):
        script = (ROOT / filename).read_text(encoding="utf-8")
        assert "requirements-dev.txt" in script
        assert "ruff check main.py tests tools" in script
        assert "ruff format --check main.py tests tools" in script
        assert "--specpath build" in script
        assert "%CD%\\assets" in script
        assert "pytest -q" in script

    assert (ROOT / "pyproject.toml").is_file()
    assert (ROOT / "requirements-dev.txt").is_file()
    assert not (ROOT / "Annota.spec").exists()


def test_windows_release_packaging_contract():
    script = (ROOT / "release_windows.bat").read_text(encoding="utf-8")
    assert "Annota-v%VERSION%-Windows-x64.zip" in script
    assert "Get-FileHash" in script
    assert "README.md" in script
    assert "LICENSE" in script


def test_macos_release_support_contract():
    build = (ROOT / "build_macos.sh").read_text(encoding="utf-8")
    release = (ROOT / "release_macos.sh").read_text(encoding="utf-8")
    kit = (ROOT / "release_macos_kit.bat").read_text(encoding="utf-8")
    guide = (ROOT / "MACOS_RELEASE.md").read_text(encoding="utf-8")

    assert "requirements-dev.txt" in build
    assert "ruff check main.py tests tools" in build
    assert "ruff format --check main.py tests tools" in build
    assert "--specpath build" in build
    assert "iconutil -c icns" in build
    assert "swiftc tools/annota_hotkey.swift" in build
    assert 'annota_hotkey "Option+Q"' in build
    assert '--add-data "$PWD/assets:assets"' in build
    assert '--add-binary "$PWD/.macos-native/annota_hotkey:."' in build
    assert "--osx-bundle-identifier net.softwify.annota" in build
    assert "dist/Annota.app" in build
    assert "MACOS_CODESIGN_IDENTITY" in build
    assert "codesign --verify --deep --strict" in build

    assert "hdiutil create" in release
    assert "MACOS_NOTARY_PROFILE" in release
    assert "shasum -a 256" in release

    assert "macOS-Build-Kit.zip" in kit
    assert "build_macos.sh" in kit
    assert "release_macos.sh" in kit
    assert "requirements-dev.txt" in kit
    assert "pyproject.toml" in kit
    assert "annota_hotkey.swift" in kit

    assert "Screen Recording" in guide
    assert "Accessibility" in guide
    assert "macOS acceptance checklist" in guide


def test_macos_github_runner_qa_contract_and_no_artifact_storage():
    workflow = (ROOT / ".github" / "workflows" / "macos-arm64-build.yml").read_text(
        encoding="utf-8"
    )
    assert "runs-on: macos-15" in workflow
    assert "actions/checkout@v6" in workflow
    assert "actions/setup-python@v6" in workflow
    assert 'python-version: "3.13"' in workflow
    assert "requirements-dev.txt" in workflow
    assert "\n  push:" not in workflow
    assert "ruff check main.py tests tools" in workflow
    assert "ruff format --check main.py tests tools" in workflow
    assert "Compile native macOS hotkey helper" in workflow
    assert "swiftc tools/annota_hotkey.swift" in workflow
    assert "Verify native Option+Q registration" in workflow
    assert 'annota_hotkey "Option+Q"' in workflow
    assert '--add-data "$PWD/assets:assets"' in workflow
    assert '--add-binary "$PWD/.macos-native/annota_hotkey:."' in workflow
    assert "Build native Annota.app" in workflow
    assert "Packaged runtime self-test" in workflow
    assert "--self-test" in workflow
    assert "Packaged launch smoke test" in workflow
    assert "--smoke-test" in workflow
    assert "hdiutil create" in workflow
    assert "gh release create" in workflow
    assert "--prerelease" in workflow
    assert "actions/upload-artifact" not in workflow
    assert "actions/download-artifact" not in workflow


def test_macos_iconset_contract():
    iconset = ROOT / "assets" / "Annota.iconset"
    expected = {
        "icon_16x16.png",
        "icon_16x16@2x.png",
        "icon_32x32.png",
        "icon_32x32@2x.png",
        "icon_128x128.png",
        "icon_128x128@2x.png",
        "icon_256x256.png",
        "icon_256x256@2x.png",
        "icon_512x512.png",
        "icon_512x512@2x.png",
    }
    assert iconset.is_dir()
    assert expected.issubset({path.name for path in iconset.iterdir()})
