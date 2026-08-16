from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_release_packaging_contract():
    script = (ROOT / "release_windows.bat").read_text(encoding="utf-8")
    assert 'VERSION=0.2.1' in script
    assert "Annota-v%VERSION%-Windows-x64.zip" in script
    assert "Get-FileHash" in script
    assert "README.md" in script
    assert "LICENSE" in script


def test_macos_release_support_contract():
    build = (ROOT / "build_macos.sh").read_text(encoding="utf-8")
    release = (ROOT / "release_macos.sh").read_text(encoding="utf-8")
    kit = (ROOT / "release_macos_kit.bat").read_text(encoding="utf-8")
    guide = (ROOT / "MACOS_RELEASE.md").read_text(encoding="utf-8")

    assert 'VERSION="0.2.1"' in build
    assert 'VERSION="0.2.1"' in release
    assert "iconutil -c icns" in build
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

    assert "Screen Recording" in guide
    assert "Accessibility" in guide
    assert "macOS acceptance checklist" in guide


def test_macos_github_runner_build_does_not_use_actions_artifact_storage():
    workflow = (ROOT / ".github" / "workflows" / "macos-arm64-build.yml").read_text(encoding="utf-8")
    assert "runs-on: macos-15" in workflow
    assert "actions/checkout@v6" in workflow
    assert "actions/setup-python@v6" in workflow
    assert 'python-version: "3.13"' in workflow
    assert "Build native Annota.app" in workflow
    assert "hdiutil create" in workflow
    assert "gh release create" in workflow
    assert "--draft" in workflow
    assert "gh release upload" in workflow
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
