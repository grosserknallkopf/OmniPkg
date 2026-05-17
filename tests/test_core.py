from __future__ import annotations

import io
import json
import tarfile
import zipfile
from pathlib import Path

import pytest

import omnipkg_core as core


def test_slugify_normalizes_names() -> None:
    assert core.slugify("  Firefox Developer Edition  ") == "firefox-developer-edition"
    assert core.slugify("Name_with.dots+symbols!") == "name_with.dots-symbols"


def test_slugify_rejects_empty_names() -> None:
    with pytest.raises(core.ApiError, match="must not be empty"):
        core.slugify(" !!! ")


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("firefox", "firefox"),
        ("@scope/tool", "@scope/tool"),
        ("libfoo:amd64", "libfoo:amd64"),
    ],
)
def test_validate_package_name_accepts_package_manager_names(name: str, expected: str) -> None:
    assert core.validate_package_name(name) == expected


@pytest.mark.parametrize("name", ["", "two words", "../../etc/passwd", "bad;command"])
def test_validate_package_name_rejects_shell_sensitive_values(name: str) -> None:
    with pytest.raises(core.ApiError, match="Invalid package name"):
        core.validate_package_name(name)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.invalid/repo",
        "http://example.invalid/repo",
        "ftp://example.invalid/repo",
        "file:///srv/repo",
    ],
)
def test_validate_source_url_accepts_repository_urls(url: str) -> None:
    assert core.validate_source_url(url) == url


@pytest.mark.parametrize("url", ["example.invalid/repo", "ssh://example.invalid/repo", "https:///missing-host"])
def test_validate_source_url_rejects_incomplete_or_unsupported_urls(url: str) -> None:
    with pytest.raises(core.ApiError):
        core.validate_source_url(url)


def test_detected_language_honors_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMNIPKG_LANG", "de_DE")
    assert core.detected_language() == "de"

    monkeypatch.setenv("OMNIPKG_LANG", "en_US")
    assert core.detected_language() == "en"


def test_parse_packagekit_package_line_strips_control_output() -> None:
    assert core.parse_packagekit_package_line("Loading cache", "apt") is None
    assert core.parse_packagekit_package_line("available firefox;123.0;amd64;ubuntu Mozilla browser", "apt") == {
        "name": "firefox",
        "packageName": "firefox",
        "version": "123.0",
        "description": "Mozilla browser",
        "source": "apt",
    }


def test_parse_apt_search_extracts_package_and_description() -> None:
    output = "firefox/stable 123 amd64\n  ignored detail\nripgrep - recursively searches directories for regex patterns\n"
    assert core.parse_apt_search(output) == [
        {
            "name": "ripgrep",
            "version": "",
            "description": "recursively searches directories for regex patterns",
            "source": "apt",
        }
    ]


def test_parse_flatpak_search_handles_table_output() -> None:
    output = "Name      Description       Application ID        Version  Branch  Remotes\nFirefox   Web browser       org.mozilla.firefox   123      stable  flathub\n"
    items = core.parse_flatpak_search(output)
    assert items[0]["id"] == "org.mozilla.firefox"
    assert items[0]["name"] == "Firefox"
    assert items[0]["source"] == "flatpak"


def test_parse_npm_search_accepts_single_object() -> None:
    items = core.parse_npm_search(json.dumps({"name": "serve", "version": "14.2.4", "description": "Static file server"}))
    assert items == [{"name": "serve", "version": "14.2.4", "description": "Static file server", "source": "npm"}]


def test_parse_pip_updates_reads_json_report() -> None:
    output = json.dumps([{"name": "black", "version": "24.4.0", "latest_version": "24.8.0"}])
    assert core.parse_pip_updates(output) == [
        {
            "name": "black",
            "packageName": "black",
            "version": "24.8.0",
            "installedVersion": "24.4.0",
            "description": "Python package update available",
            "source": "pip",
        }
    ]


def test_preferences_round_trip_uses_config_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    monkeypatch.setattr(core, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(core, "PREFERENCES_PATH", config_dir / "preferences.json")

    core.write_preferences({"frontend": "qt"})

    assert core.read_preferences() == {"frontend": "qt"}
    assert core.frontend_preference() == "qt"


def test_safe_extract_tar_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.tar"
    with tarfile.open(archive, "w") as tar:
        data = b"escape"
        info = tarfile.TarInfo("../escape.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    with pytest.raises(core.ApiError, match="unsafe paths"):
        core.safe_extract_tar(archive, tmp_path / "target")


def test_safe_extract_tar_rejects_links_outside_target(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe-link.tar"
    with tarfile.open(archive, "w") as tar:
        info = tarfile.TarInfo("link")
        info.type = tarfile.SYMTYPE
        info.linkname = "../outside"
        tar.addfile(info)

    with pytest.raises(core.ApiError, match="unsafe links"):
        core.safe_extract_tar(archive, tmp_path / "target")


def test_safe_extract_tar_extracts_regular_files(tmp_path: Path) -> None:
    archive = tmp_path / "safe.tar"
    with tarfile.open(archive, "w") as tar:
        data = b"hello"
        info = tarfile.TarInfo("app/readme.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    target = tmp_path / "target"
    core.safe_extract_tar(archive, target)

    assert (target / "app" / "readme.txt").read_text(encoding="utf-8") == "hello"


def test_safe_extract_zip_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as zip_ref:
        zip_ref.writestr("../escape.txt", "escape")

    with pytest.raises(core.ApiError, match="unsafe paths"):
        core.safe_extract_zip(archive, tmp_path / "target")


def test_resolve_frontend_falls_back_when_preferred_frontend_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(core, "frontend_preference", lambda: "qt")
    monkeypatch.setattr(core, "qt_frontend_available", lambda: False)
    monkeypatch.setattr(core, "gtk_frontend_available", lambda: True)

    assert core.resolve_frontend() == "gtk"
