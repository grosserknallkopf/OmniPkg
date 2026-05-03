#!/usr/bin/env python3
"""Package-management core for OmniPkg.

The module intentionally uses only the Python standard library. It can still
serve the early web prototype, but the primary UI is the native GTK app.
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import shutil
import subprocess
import tarfile
import threading
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


APP_NAME = "OmniPkg"
HOST = "127.0.0.1"
DEFAULT_PORT = 8765
ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
CONFIG_DIR = DATA_HOME / "omnipkg"
LEGACY_CONFIG_DIR = DATA_HOME / "arch-software-manager"
REGISTRY_PATH = CONFIG_DIR / "registry.json"
LEGACY_REGISTRY_PATH = LEGACY_CONFIG_DIR / "registry.json"
APPIMAGE_DIR = Path.home() / ".local" / "opt" / "omnipkg" / "appimages"
ARCHIVE_DIR = Path.home() / ".local" / "opt" / "omnipkg" / "apps"
LEGACY_APPIMAGE_DIR = Path.home() / ".local" / "opt" / "arch-software-manager" / "appimages"
LEGACY_ARCHIVE_DIR = Path.home() / ".local" / "opt" / "arch-software-manager" / "apps"
BIN_DIR = Path.home() / ".local" / "bin"
APPLICATIONS_DIR = DATA_HOME / "applications"
ICON_DIR = DATA_HOME / "icons" / "hicolor" / "512x512" / "apps"
PACKAGE_RE = re.compile(r"^[A-Za-z0-9@._+:/=-]+$")
SOURCE_ORDER = (
    "apt",
    "dnf",
    "zypper",
    "pacman",
    "aur",
    "apk",
    "xbps",
    "eopkg",
    "flatpak",
    "snap",
    "brew",
    "npm",
    "pip",
    "manual",
    "desktop",
)
DESKTOP_DIRS = (
    Path("/usr/share/applications"),
    Path("/usr/local/share/applications"),
    DATA_HOME / "applications",
    Path("/var/lib/flatpak/exports/share/applications"),
    DATA_HOME / "flatpak" / "exports" / "share" / "applications",
    Path("/var/lib/snapd/desktop/applications"),
)
APPSTREAM_ICON_DIRS = (
    Path("/var/lib/flatpak/appstream"),
    DATA_HOME / "flatpak" / "appstream",
    Path("/var/lib/swcatalog/icons"),
    Path("/usr/share/swcatalog/icons"),
    Path("/var/cache/app-info/icons"),
    Path("/usr/share/app-info/icons"),
)
ICON_LOOKUP_DIRS = (
    DATA_HOME / "icons",
    DATA_HOME / "pixmaps",
    Path("/usr/local/share/icons"),
    Path("/usr/share/icons"),
    Path("/usr/local/share/pixmaps"),
    Path("/usr/share/pixmaps"),
)


@dataclass
class Job:
    id: str
    label: str
    command: list[str]
    created_at: float = field(default_factory=time.time)
    state: str = "queued"
    exit_code: int | None = None
    output: list[str] = field(default_factory=list)


JOBS: dict[str, Job] = {}
JOBS_LOCK = threading.Lock()


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def now_ms() -> int:
    return int(time.time() * 1000)


def which(binary: str) -> str | None:
    return shutil.which(binary)


def run_capture(command: list[str], timeout: int = 20) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout
    except FileNotFoundError:
        return 127, f"{command[0]} was not found."
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        return 124, output + "\nTimeout reached."


def require_binary(binary: str) -> str:
    found = which(binary)
    if not found:
        raise ApiError(f"{binary} is not installed or not in PATH.", 404)
    return found


def detected_language() -> str:
    override = os.environ.get("OMNIPKG_LANG", "").strip().lower()
    if override.startswith(("de", "en")):
        return override[:2]
    for value in (
        os.environ.get("LANGUAGE", ""),
        os.environ.get("LANG", ""),
        os.environ.get("LC_MESSAGES", ""),
        os.environ.get("LC_ALL", ""),
    ):
        primary = value.split(":", 1)[0].split(".", 1)[0].replace("_", "-").lower()
        if primary.startswith("de"):
            return "de"
    return "en"


def desktop_entry_value(entry: configparser.SectionProxy, key: str) -> str:
    if detected_language() == "de":
        return entry.get(f"{key}[de_DE]") or entry.get(f"{key}[de]") or entry.get(key, "")
    return entry.get(key, "")


def aur_helper() -> str | None:
    for helper in ("yay", "paru"):
        if which(helper):
            return helper
    return None


def aur_sudo_options() -> list[str]:
    if os.environ.get("SUDO_ASKPASS"):
        return ["--sudoflags=-A", "--sudoloop"]
    return []


def python_executable() -> str | None:
    for binary in ("python3", "python"):
        found = which(binary)
        if found:
            return found
    return None


def require_python_pip() -> str:
    python = python_executable()
    if not python:
        raise ApiError("python3 was not found.", 404)
    code, output = run_capture([python, "-m", "pip", "--version"])
    if code != 0:
        raise ApiError("pip is not available for this Python: " + output.strip(), 404)
    return python


def apt_available() -> bool:
    return bool(which("apt-cache") and which("apt-get") and which("dpkg-query"))


def require_apt() -> None:
    if not apt_available():
        raise ApiError("APT is not installed or not fully available in PATH.", 404)


def dnf_binary() -> str | None:
    return which("dnf5") or which("dnf")


def zypper_available() -> bool:
    return bool(which("zypper"))


def apk_available() -> bool:
    return bool(which("apk"))


def xbps_available() -> bool:
    return bool(which("xbps-query") and which("xbps-install") and which("xbps-remove"))


def eopkg_available() -> bool:
    return bool(which("eopkg"))


def native_package_source() -> str:
    if apt_available():
        return "apt"
    if dnf_binary():
        return "dnf"
    if zypper_available():
        return "zypper"
    if which("pacman"):
        return "pacman"
    if apk_available():
        return "apk"
    if xbps_available():
        return "xbps"
    if eopkg_available():
        return "eopkg"
    return ""


def validate_package_name(name: str) -> str:
    name = name.strip()
    if not name or not PACKAGE_RE.match(name):
        raise ApiError("Invalid package name.")
    return name


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip(".-").lower()
    if not slug:
        raise ApiError("The name must not be empty.")
    return slug[:80]


def privileged(command: list[str]) -> list[str]:
    if os.geteuid() == 0:
        return command
    if os.environ.get("SUDO_ASKPASS") and which("sudo"):
        return ["sudo", "-A", *command]
    if which("pkexec"):
        return ["pkexec", *command]
    if which("sudo"):
        return ["sudo", *command]
    raise ApiError("Neither pkexec nor sudo was found.")


def read_registry() -> dict[str, Any]:
    source_path = REGISTRY_PATH
    if not source_path.exists() and LEGACY_REGISTRY_PATH.exists():
        source_path = LEGACY_REGISTRY_PATH
    if not source_path.exists():
        return {"manual": []}
    try:
        with source_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"manual": []}
    if not isinstance(data, dict) or not isinstance(data.get("manual"), list):
        return {"manual": []}
    return data


def write_registry(data: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = REGISTRY_PATH.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
    tmp_path.replace(REGISTRY_PATH)


def register_manual(entry: dict[str, Any]) -> dict[str, Any]:
    data = read_registry()
    entries = [item for item in data.get("manual", []) if item.get("id") != entry["id"]]
    entries.append(entry)
    data["manual"] = sorted(entries, key=lambda item: item.get("name", "").lower())
    write_registry(data)
    return entry


def remove_registry_entry(identifier: str) -> dict[str, Any]:
    data = read_registry()
    entries = data.get("manual", [])
    match = next((item for item in entries if item.get("id") == identifier), None)
    if not match:
        raise ApiError("Manual entry was not found.", 404)
    data["manual"] = [item for item in entries if item.get("id") != identifier]
    write_registry(data)
    return match


def safe_path(value: str) -> Path:
    if not value:
        raise ApiError("Path is missing.")
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise ApiError(f"{path} does not exist.", 404)
    return path


def safe_extract_tar(archive: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tar:
        target_resolved = target.resolve()
        for member in tar.getmembers():
            member_path = (target / member.name).resolve()
            if target_resolved not in member_path.parents and member_path != target_resolved:
                raise ApiError("Archive contains unsafe paths.")
        tar.extractall(target)


def safe_extract_zip(archive: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zip_ref:
        target_resolved = target.resolve()
        for member in zip_ref.namelist():
            member_path = (target / member).resolve()
            if target_resolved not in member_path.parents and member_path != target_resolved:
                raise ApiError("Archive contains unsafe paths.")
        zip_ref.extractall(target)


def copy_icon(icon_path: Path | None, slug: str) -> str | None:
    if not icon_path:
        return None
    if icon_path.suffix.lower() not in {".png", ".svg", ".jpg", ".jpeg", ".webp"}:
        raise ApiError("Icon must be PNG, SVG, JPG or WEBP.")
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    target = ICON_DIR / f"{slug}{icon_path.suffix.lower()}"
    shutil.copy2(icon_path, target)
    return str(target)


def desktop_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", " ").replace('"', '\\"')


def create_desktop_file(slug: str, name: str, exec_path: Path, icon_path: str | None) -> str:
    APPLICATIONS_DIR.mkdir(parents=True, exist_ok=True)
    desktop_path = APPLICATIONS_DIR / f"{slug}.desktop"
    icon_line = f"Icon={desktop_escape(icon_path)}\n" if icon_path else ""
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={desktop_escape(name)}\n"
        f"Exec={desktop_escape(str(exec_path))} %U\n"
        f"{icon_line}"
        "Terminal=false\n"
        "Categories=Utility;Application;\n"
        "StartupNotify=true\n"
    )
    desktop_path.write_text(content, encoding="utf-8")
    desktop_path.chmod(0o755)
    if which("update-desktop-database"):
        subprocess.run(["update-desktop-database", str(APPLICATIONS_DIR)], check=False)
    return str(desktop_path)


def parse_desktop_file(path: Path) -> dict[str, Any] | None:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    try:
        parser.read(path, encoding="utf-8")
    except (configparser.Error, UnicodeDecodeError, OSError):
        return None
    if "Desktop Entry" not in parser:
        return None
    entry = parser["Desktop Entry"]
    if entry.get("Type", "Application") != "Application":
        return None
    if entry.getboolean("Hidden", fallback=False):
        return None
    name = desktop_entry_value(entry, "Name")
    if not name:
        return None
    desktop_id = path.name
    source = "desktop"
    if "flatpak/exports" in str(path):
        source = "flatpak"
    elif "snapd/desktop" in str(path):
        source = "snap"
    elif CONFIG_DIR.name in path.name or path.name.startswith("omnipkg"):
        source = "manual"
    return {
        "desktopId": desktop_id,
        "desktopPath": str(path),
        "name": name,
        "genericName": desktop_entry_value(entry, "GenericName"),
        "description": desktop_entry_value(entry, "Comment"),
        "icon": entry.get("Icon", ""),
        "exec": entry.get("Exec", ""),
        "categories": entry.get("Categories", ""),
        "noDisplay": entry.getboolean("NoDisplay", fallback=False),
        "terminal": entry.getboolean("Terminal", fallback=False),
        "sourceHint": source,
    }


def desktop_entries(include_hidden: bool = False) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for directory in DESKTOP_DIRS:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.desktop")):
            if path.name in seen:
                continue
            item = parse_desktop_file(path)
            if not item:
                continue
            seen.add(path.name)
            if item.get("noDisplay") and not include_hidden:
                continue
            entries.append(item)
    return entries


def package_owners(paths: list[str], source: str) -> dict[str, str]:
    if not paths:
        return {}
    owners: dict[str, str] = {}
    if source in {"pacman", "aur"} and which("pacman"):
        code, output = run_capture(["pacman", "-Qo", *paths], timeout=45)
        if code == 127:
            return owners
        for line in output.splitlines():
            match = re.match(r"^(.+) is owned by (\S+) ", line)
            if match:
                owners[match.group(1)] = match.group(2)
        return owners
    if source in {"dnf", "zypper"} and which("rpm"):
        for path in paths:
            code, output = run_capture(["rpm", "-qf", "--qf", "%{NAME}\n", path], timeout=10)
            if code == 0:
                package = output.splitlines()[0].strip()
                if package:
                    owners[path] = package
        return owners
    if source == "apt" and which("dpkg-query"):
        for path in paths:
            code, output = run_capture(["dpkg-query", "-S", path], timeout=10)
            if code == 0 and ":" in output:
                owners[path] = output.split(":", 1)[0].split(",", 1)[0].strip()
        return owners
    return owners


def desktop_package_index() -> dict[tuple[str, str], dict[str, Any]]:
    entries = desktop_entries(include_hidden=False)
    index: dict[tuple[str, str], dict[str, Any]] = {}

    native_paths = [
        item["desktopPath"]
        for item in entries
        if item.get("sourceHint") == "desktop" and item.get("desktopPath", "").startswith(("/usr/share", "/usr/local/share"))
    ]
    native_source = native_package_source()
    owners = package_owners(native_paths, native_source) if native_source else {}

    for item in entries:
        desktop_path = item.get("desktopPath", "")
        desktop_id = item.get("desktopId", "")
        source_hint = item.get("sourceHint")
        package = owners.get(desktop_path, "")
        source = native_source if package else source_hint
        if source_hint == "flatpak":
            package = desktop_id.removesuffix(".desktop")
            source = "flatpak"
        elif source_hint == "snap":
            package = desktop_id.split("_", 1)[0].removesuffix(".desktop")
            source = "snap"
        elif source_hint == "manual":
            package = desktop_id.removesuffix(".desktop")
            source = "manual"
        if source and package:
            enriched = {**item, "source": source, "package": package, "gui": True}
            index[(source, package)] = enriched
            index[(source, desktop_id.removesuffix(".desktop"))] = enriched
        elif source_hint == "desktop":
            package = desktop_id.removesuffix(".desktop")
            enriched = {**item, "source": "desktop", "package": package, "gui": True}
            index[("desktop", package)] = enriched
    return index


def find_appstream_icon(icon: str) -> str:
    if not icon:
        return ""
    icon_path = Path(icon)
    if icon_path.is_absolute() and icon_path.exists():
        return str(icon_path)
    candidates = {icon, icon.removesuffix(".png"), icon.removesuffix(".svg")}
    for directory in APPSTREAM_ICON_DIRS:
        if not directory.exists():
            continue
        for candidate in candidates:
            for path in directory.rglob(candidate):
                if path.is_file():
                    return str(path)
            for suffix in (".png", ".svg", ".webp"):
                for path in directory.rglob(candidate + suffix):
                    if path.is_file():
                        return str(path)
    return find_theme_icon(icon) or icon


def find_theme_icon(icon: str) -> str:
    if not icon:
        return ""
    icon_path = Path(icon).expanduser()
    if icon_path.is_absolute() and icon_path.exists():
        return str(icon_path)
    base = re.sub(r"\.(png|svg|webp|jpg|jpeg)$", "", icon, flags=re.IGNORECASE)
    names = [base + suffix for suffix in (".png", ".svg", ".webp", ".jpg", ".jpeg")]
    preferred = ("512x512", "256x256", "128x128", "64x64", "48x48", "scalable")
    matches: list[Path] = []
    for root in ICON_LOOKUP_DIRS:
        if not root.exists():
            continue
        if root.name == "pixmaps":
            for name in names:
                candidate = root / name
                if candidate.exists():
                    matches.append(candidate)
            continue
        for size in preferred:
            for name in names:
                candidate = root / "hicolor" / size / "apps" / name
                if candidate.exists():
                    matches.append(candidate)
                candidate = root / size / "apps" / name
                if candidate.exists():
                    matches.append(candidate)
        if not matches:
            for name in names:
                matches.extend(root.glob(f"*/**/apps/{name}"))
    if not matches:
        return ""
    def score(path: Path) -> int:
        text = str(path)
        for index, size in enumerate(preferred):
            if size in text:
                return index
        return len(preferred)
    return str(sorted(matches, key=score)[0])


def enrich_item(item: dict[str, Any], desktop_index: dict[tuple[str, str], dict[str, Any]] | None = None) -> dict[str, Any]:
    desktop_index = desktop_index if desktop_index is not None else desktop_package_index()
    source = str(item.get("source", ""))
    keys = [str(item.get("name", "")), str(item.get("id", ""))]
    desktop = next((desktop_index.get((source, key)) for key in keys if key), None)
    enriched = dict(item)
    if desktop:
        enriched["packageName"] = item.get("name") or item.get("id")
        enriched["name"] = desktop.get("name") or enriched.get("name")
        enriched["description"] = desktop.get("description") or enriched.get("description", "")
        enriched["icon"] = find_theme_icon(str(desktop.get("icon", ""))) or desktop.get("icon", "")
        enriched["desktopId"] = desktop.get("desktopId")
        enriched["desktopPath"] = desktop.get("desktopPath")
        enriched["gui"] = True
    else:
        enriched.setdefault("gui", False)
    return enriched


def search_desktop_apps(query: str, desktop_index: dict[tuple[str, str], dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    term = query.casefold().strip()
    if not term:
        return []
    desktop_index = desktop_index if desktop_index is not None else desktop_package_index()
    results = []
    seen: set[str] = set()
    for item in desktop_index.values():
        if item.get("source") == "desktop":
            continue
        desktop_id = str(item.get("desktopId", ""))
        if not desktop_id or desktop_id in seen:
            continue
        haystack = " ".join(
            str(item.get(key, ""))
            for key in ("name", "genericName", "description", "package", "desktopId", "categories")
        ).casefold()
        if term not in haystack:
            continue
        seen.add(desktop_id)
        results.append(
            {
                "id": item.get("package"),
                "name": item.get("name", item.get("package", "")),
                "packageName": item.get("package"),
                "version": "",
                "source": item.get("source", "desktop"),
                "description": item.get("description", ""),
                "icon": find_theme_icon(str(item.get("icon", ""))) or item.get("icon", ""),
                "desktopId": desktop_id,
                "desktopPath": item.get("desktopPath", ""),
                "gui": True,
            }
        )
    return results


def list_pacman_installed(aur_only: bool = False) -> list[dict[str, Any]]:
    command = ["pacman", "-Qm" if aur_only else "-Qn"]
    code, output = run_capture(command)
    if code != 0:
        return []
    items = []
    for line in output.splitlines():
        parts = line.split(maxsplit=1)
        if parts:
            items.append(
                {
                    "name": parts[0],
                    "version": parts[1] if len(parts) > 1 else "",
                    "source": "aur" if aur_only else "pacman",
                }
            )
    return items


def list_apt_installed() -> list[dict[str, Any]]:
    if not apt_available():
        return []
    code, output = run_capture(["dpkg-query", "-W", "-f=${binary:Package}\t${Version}\n"], timeout=45)
    if code != 0:
        return []
    items = []
    for line in output.splitlines():
        parts = line.split("\t", 1)
        if parts and parts[0]:
            items.append({"name": parts[0], "version": parts[1] if len(parts) > 1 else "", "source": "apt"})
    return items


def list_rpm_installed(source: str) -> list[dict[str, Any]]:
    if not which("rpm"):
        return []
    code, output = run_capture(["rpm", "-qa", "--qf", "%{NAME}\t%{VERSION}-%{RELEASE}\n"], timeout=45)
    if code != 0:
        return []
    items = []
    for line in output.splitlines():
        parts = line.split("\t", 1)
        if parts and parts[0]:
            items.append({"name": parts[0], "version": parts[1] if len(parts) > 1 else "", "source": source})
    return items


def list_apk_installed() -> list[dict[str, Any]]:
    if not apk_available():
        return []
    code, output = run_capture(["apk", "info", "-v"], timeout=30)
    if code != 0:
        return []
    return [{"name": line.strip(), "version": "", "source": "apk"} for line in output.splitlines() if line.strip()]


def list_xbps_installed() -> list[dict[str, Any]]:
    if not xbps_available():
        return []
    code, output = run_capture(["xbps-query", "-l"], timeout=45)
    if code != 0:
        return []
    items = []
    for line in output.splitlines():
        parts = line.split(maxsplit=2)
        if len(parts) >= 2:
            name_version = parts[1]
            name, version = name_version, ""
            if "-" in name_version:
                name, version = name_version.rsplit("-", 1)
            items.append({"name": name, "version": version, "source": "xbps"})
    return items


def list_eopkg_installed() -> list[dict[str, Any]]:
    if not eopkg_available():
        return []
    code, output = run_capture(["eopkg", "list-installed"], timeout=45)
    if code != 0:
        return []
    items = []
    for line in output.splitlines():
        parts = line.split(" - ", 1)
        first = parts[0].split()
        if first:
            items.append({"name": first[0], "version": first[1] if len(first) > 1 else "", "source": "eopkg"})
    return items


def list_flatpak_installed() -> list[dict[str, Any]]:
    if not which("flatpak"):
        return []
    code, output = run_capture(["flatpak", "list", "--app", "--columns=application,name,version,origin"])
    if code != 0:
        return []
    items = []
    for line in output.splitlines():
        parts = line.split("\t")
        if parts and parts[0]:
            items.append(
                {
                    "id": parts[0],
                    "name": parts[1] if len(parts) > 1 and parts[1] else parts[0],
                    "version": parts[2] if len(parts) > 2 else "",
                    "source": "flatpak",
                    "origin": parts[3] if len(parts) > 3 else "",
                    "gui": True,
                }
            )
    return items


def list_snap_installed() -> list[dict[str, Any]]:
    if not which("snap"):
        return []
    code, output = run_capture(["snap", "list"])
    if code != 0:
        return []
    items = []
    for line in output.splitlines()[1:]:
        parts = line.split()
        if parts:
            items.append(
                {
                    "name": parts[0],
                    "version": parts[1] if len(parts) > 1 else "",
                    "source": "snap",
                }
            )
    return items


def list_brew_installed() -> list[dict[str, Any]]:
    if not which("brew"):
        return []
    code, output = run_capture(["brew", "list", "--versions"], timeout=30)
    if code != 0:
        return []
    items = []
    for line in output.splitlines():
        parts = line.split()
        if parts:
            items.append(
                {
                    "name": parts[0],
                    "version": " ".join(parts[1:]),
                    "source": "brew",
                }
            )
    return items


def list_npm_installed() -> list[dict[str, Any]]:
    if not which("npm"):
        return []
    code, output = run_capture(["npm", "-g", "ls", "--depth=0", "--json"], timeout=30)
    if code not in (0, 1):
        return []
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return []
    deps = data.get("dependencies", {})
    return [
        {"name": name, "version": meta.get("version", ""), "source": "npm"}
        for name, meta in sorted(deps.items())
    ]


def list_pip_installed() -> list[dict[str, Any]]:
    python = python_executable()
    if not python:
        return []
    code, output = run_capture([python, "-m", "pip", "list", "--user", "--format=json"], timeout=30)
    if code != 0:
        return []
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return []
    return [
        {"name": item.get("name", ""), "version": item.get("version", ""), "source": "pip"}
        for item in data
        if isinstance(item, dict) and item.get("name")
    ]


def list_manual_installed() -> list[dict[str, Any]]:
    return [
        {
            "id": item.get("id"),
            "name": item.get("name", item.get("id", "")),
            "version": item.get("version", ""),
            "source": "manual",
            "kind": item.get("kind", ""),
            "path": item.get("path", ""),
            "icon": item.get("icon", ""),
            "desktopPath": item.get("desktop", ""),
            "gui": bool(item.get("desktop")),
        }
        for item in read_registry().get("manual", [])
    ]


def list_desktop_installed() -> list[dict[str, Any]]:
    desktop_index = desktop_package_index()
    native_items = []
    known_keys = {
        (item.get("source"), item.get("package"))
        for item in desktop_index.values()
        if item.get("source") in set(SOURCE_ORDER) - {"desktop"}
    }
    seen: set[str] = set()
    for item in desktop_index.values():
        desktop_id = item.get("desktopId", "")
        if not desktop_id or desktop_id in seen:
            continue
        seen.add(desktop_id)
        if (item.get("source"), item.get("package")) in known_keys and item.get("source") != "desktop":
            continue
        if item.get("source") != "desktop":
            continue
        native_items.append(
            {
                "id": item.get("package"),
                "name": item.get("name", item.get("package", "")),
                "packageName": item.get("package"),
                "version": "",
                "source": "desktop",
                "description": item.get("description", ""),
                "icon": item.get("icon", ""),
                "desktopId": desktop_id,
                "desktopPath": item.get("desktopPath", ""),
                "gui": True,
            }
        )
    return native_items


def parse_pacman_search(output: str, source: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in output.splitlines():
        if not line.strip():
            continue
        match = re.match(r"^([^/\s]+)/([^\s]+)\s+(.+)$", line)
        if match:
            if current:
                results.append(current)
            repo, name, version = match.groups()
            current = {"repo": repo, "name": name, "version": version, "description": "", "source": source}
        elif current:
            current["description"] = (current.get("description", "") + " " + line.strip()).strip()
    if current:
        results.append(current)
    return results[:80]


def parse_simple_lines(output: str, source: str) -> list[dict[str, Any]]:
    items = []
    for line in output.splitlines():
        name = line.strip()
        if name:
            items.append({"name": name, "version": "", "description": "", "source": source})
    return items[:80]


def parse_apt_search(output: str) -> list[dict[str, Any]]:
    items = []
    for line in output.splitlines():
        if " - " not in line:
            continue
        name, description = line.split(" - ", 1)
        package = name.split("/", 1)[0].strip()
        if package:
            items.append({"name": package, "version": "", "description": description.strip(), "source": "apt"})
    return items[:80]


def parse_dnf_search(output: str) -> list[dict[str, Any]]:
    items = []
    for line in output.splitlines():
        if " : " not in line:
            continue
        left, description = line.split(" : ", 1)
        name = left.strip().split()[0].rsplit(".", 1)[0]
        if name:
            items.append({"name": name, "version": "", "description": description.strip(), "source": "dnf"})
    return items[:80]


def parse_zypper_search(output: str) -> list[dict[str, Any]]:
    items = []
    for line in output.splitlines():
        if "|" not in line or line.lstrip().startswith(("-", "S ")):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) >= 3 and parts[1] and parts[1].lower() != "name":
            items.append(
                {
                    "name": parts[1],
                    "version": parts[3] if len(parts) > 3 else "",
                    "description": parts[2],
                    "source": "zypper",
                }
            )
    return items[:80]


def parse_apk_search(output: str) -> list[dict[str, Any]]:
    items = []
    for line in output.splitlines():
        text = line.strip()
        if not text:
            continue
        package = text.split()[0]
        name = package.rsplit("-", 1)[0] if "-" in package else package
        items.append({"name": name, "version": "", "description": text, "source": "apk"})
    return items[:80]


def parse_xbps_search(output: str) -> list[dict[str, Any]]:
    items = []
    for line in output.splitlines():
        text = line.strip()
        if not text:
            continue
        parts = text.split(maxsplit=2)
        if len(parts) >= 2:
            name_version = parts[1]
            name, version = name_version, ""
            if "-" in name_version:
                name, version = name_version.rsplit("-", 1)
            items.append({"name": name, "version": version, "description": parts[2] if len(parts) > 2 else "", "source": "xbps"})
    return items[:80]


def parse_eopkg_search(output: str) -> list[dict[str, Any]]:
    items = []
    for line in output.splitlines():
        text = line.strip()
        if not text or text.startswith(("Searching", "Package")):
            continue
        parts = text.split(" - ", 1)
        name = parts[0].split()[0]
        if name:
            items.append({"name": name, "version": "", "description": parts[1] if len(parts) > 1 else "", "source": "eopkg"})
    return items[:80]


def parse_flatpak_search(output: str) -> list[dict[str, Any]]:
    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    if lines and lines[0].lower().startswith(("application", "name")):
        lines = lines[1:]
    items = []
    for line in lines:
        parts = re.split(r"\s{2,}", line.strip())
        if not parts:
            continue
        app_id = next((part for part in parts if "." in part and " " not in part), parts[0])
        name = parts[1] if len(parts) > 1 and parts[0] == app_id else parts[0]
        description = " ".join(part for part in parts if part not in {app_id, name})
        items.append({"id": app_id, "name": name, "description": description, "version": "", "source": "flatpak"})
    return items[:50]


def parse_snap_search(output: str) -> list[dict[str, Any]]:
    lines = [line for line in output.splitlines() if line.strip()]
    if lines and lines[0].lower().startswith("name"):
        lines = lines[1:]
    items = []
    for line in lines:
        parts = line.split(maxsplit=5)
        if parts:
            items.append(
                {
                    "name": parts[0],
                    "version": parts[1] if len(parts) > 1 else "",
                    "description": parts[5] if len(parts) > 5 else "",
                    "source": "snap",
                }
            )
    return items[:50]


def parse_npm_search(output: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = [data]
    items = []
    for item in data[:50]:
        if not isinstance(item, dict):
            continue
        items.append(
            {
                "name": item.get("name", ""),
                "version": item.get("version", ""),
                "description": item.get("description", ""),
                "source": "npm",
            }
        )
    return items


def parse_pip_index(output: str, query: str) -> list[dict[str, Any]]:
    name = query.strip()
    versions = ""
    latest = ""
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("available versions:"):
            versions = stripped.split(":", 1)[1].strip()
        elif stripped.lower().startswith("latest:"):
            latest = stripped.split(":", 1)[1].strip()
    if not versions and not latest:
        return []
    return [
        {
            "name": name,
            "version": latest or versions.split(",")[0].strip(),
            "description": "PyPI package. pip can reliably check exact names only.",
            "source": "pip",
        }
    ]


def parse_appstream_search(output: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "---":
            if current:
                items.append(current)
                current = {}
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        value = value.strip()
        if key == "Identifier":
            match = re.match(r"(.+?)\s+\[(.+)]$", value)
            if match:
                current["id"] = match.group(1).strip()
                current["componentKind"] = match.group(2).strip()
            else:
                current["id"] = value
        elif key == "Name":
            current["name"] = value
        elif key == "Summary":
            current["description"] = value
        elif key == "Package":
            current["package"] = value
        elif key == "Bundle":
            current["bundle"] = value
        elif key == "Icon":
            current["icon"] = find_appstream_icon(value)
    if current:
        items.append(current)

    results: list[dict[str, Any]] = []
    for item in items:
        source = ""
        name = item.get("package") or item.get("id", "")
        bundle = str(item.get("bundle", ""))
        if bundle.startswith("flatpak:"):
            source = "flatpak"
            parts = bundle.split("/")
            if len(parts) >= 2:
                name = parts[1]
        elif item.get("package"):
            source = native_package_source()
        if not source or not name:
            continue
        results.append(
            {
                "id": item.get("id"),
                "name": item.get("name") or name,
                "packageName": name,
                "version": "",
                "description": item.get("description", ""),
                "source": source,
                "icon": item.get("icon", ""),
                "gui": item.get("componentKind") == "desktop-application",
                "componentKind": item.get("componentKind", ""),
            }
        )
    return results[:120]


def search_appstream(query: str) -> list[dict[str, Any]]:
    if not which("appstreamcli"):
        return []
    code, output = run_capture(["appstreamcli", "search", query], timeout=45)
    if code not in (0, 1):
        return []
    return parse_appstream_search(output)


def search_packages(source: str, query: str) -> list[dict[str, Any]]:
    query = query.strip()
    if len(query) < 2:
        return []
    if source == "apt":
        require_apt()
        code, output = run_capture(["apt-cache", "search", query], timeout=30)
        return parse_apt_search(output) if code in (0, 1) else []
    if source == "dnf":
        dnf = dnf_binary()
        if not dnf:
            raise ApiError("dnf is not installed or not in PATH.", 404)
        code, output = run_capture([dnf, "search", query], timeout=30)
        return parse_dnf_search(output) if code in (0, 1) else []
    if source == "zypper":
        require_binary("zypper")
        code, output = run_capture(["zypper", "--non-interactive", "search", "-s", query], timeout=30)
        return parse_zypper_search(output) if code in (0, 1) else []
    if source == "pacman":
        require_binary("pacman")
        code, output = run_capture(["pacman", "-Ss", "--color=never", query], timeout=30)
        return parse_pacman_search(output, "pacman") if code in (0, 1) else []
    if source == "aur":
        helper = aur_helper()
        if not helper:
            raise ApiError("Install yay or paru to search the AUR.", 404)
        code, output = run_capture([helper, "-Ss", "--color=never", query], timeout=45)
        return parse_pacman_search(output, "aur") if code in (0, 1) else []
    if source == "apk":
        require_binary("apk")
        code, output = run_capture(["apk", "search", query], timeout=30)
        return parse_apk_search(output) if code in (0, 1) else []
    if source == "xbps":
        require_binary("xbps-query")
        code, output = run_capture(["xbps-query", "-Rs", query], timeout=30)
        return parse_xbps_search(output) if code in (0, 1) else []
    if source == "eopkg":
        require_binary("eopkg")
        code, output = run_capture(["eopkg", "search", query], timeout=30)
        return parse_eopkg_search(output) if code in (0, 1) else []
    if source == "flatpak":
        require_binary("flatpak")
        code, output = run_capture(["flatpak", "search", query], timeout=30)
        return parse_flatpak_search(output) if code in (0, 1) else []
    if source == "snap":
        require_binary("snap")
        code, output = run_capture(["snap", "find", query], timeout=30)
        return parse_snap_search(output) if code in (0, 1) else []
    if source == "brew":
        require_binary("brew")
        code, output = run_capture(["brew", "search", query], timeout=30)
        return parse_simple_lines(output, "brew") if code in (0, 1) else []
    if source == "npm":
        require_binary("npm")
        code, output = run_capture(["npm", "search", "--json", "--searchlimit=50", query], timeout=45)
        return parse_npm_search(output) if code in (0, 1) else []
    if source == "pip":
        python = require_python_pip()
        code, output = run_capture([python, "-m", "pip", "index", "versions", query], timeout=45)
        return parse_pip_index(output, query) if code in (0, 1) else []
    raise ApiError("Unknown source.", 404)


def search_all_packages(query: str, include_non_gui: bool = True) -> list[dict[str, Any]]:
    query = query.strip()
    if len(query) < 2:
        return []
    term = query.casefold()
    desktop_index = desktop_package_index()
    results: dict[tuple[str, str], dict[str, Any]] = {}

    def result_key(item: dict[str, Any]) -> tuple[str, str]:
        source = str(item.get("source", ""))
        if item.get("gui"):
            app_id = str(item.get("desktopId") or item.get("id") or "")
            if app_id:
                return source, app_id
        return source, str(item.get("packageName") or item.get("id") or item.get("name"))

    seen_named_packages: set[tuple[str, str, str]] = set()

    def named_package_key(item: dict[str, Any]) -> tuple[str, str, str] | None:
        source = str(item.get("source", ""))
        package = str(item.get("packageName") or item.get("id") or "")
        name = str(item.get("name") or "")
        if source and package and name:
            return source, package.casefold(), name.casefold()
        return None

    def add_result(item: dict[str, Any]) -> None:
        key = result_key(item)
        named_key = named_package_key(item)
        if named_key and named_key in seen_named_packages and key not in results:
            return
        if key not in results or not results[key].get("gui"):
            results[key] = item
        if named_key:
            seen_named_packages.add(named_key)

    for item in search_desktop_apps(query, desktop_index):
        add_result(item)
    for item in search_appstream(query):
        if not include_non_gui and not item.get("gui"):
            continue
        enriched = enrich_item(item, desktop_index)
        add_result(enriched)

    if include_non_gui:
        for source in SOURCE_ORDER:
            if source in {"manual", "desktop"}:
                continue
            try:
                items = search_packages(source, query)
            except ApiError:
                continue
            for item in items:
                enriched = enrich_item(item, desktop_index)
                key = result_key(enriched)
                if key in results and results[key].get("gui"):
                    continue
                add_result(enriched)

    def relevance(item: dict[str, Any]) -> int:
        name = str(item.get("name", "")).casefold()
        package = str(item.get("packageName") or item.get("id") or "").casefold()
        desktop_id = str(item.get("desktopId") or item.get("id") or "").casefold()
        description = str(item.get("description", "")).casefold()
        if term in {name, package, desktop_id}:
            return 0
        if name.startswith(term) or package.startswith(term) or desktop_id.startswith(term):
            return 1
        if term in name or term in package or term in desktop_id:
            return 2
        if term in description:
            return 3
        return 4

    return sorted(
        results.values(),
        key=lambda item: (
            relevance(item),
            0 if item.get("gui") else 1,
            SOURCE_ORDER.index(item.get("source")) if item.get("source") in SOURCE_ORDER else 99,
            str(item.get("name", "")).lower(),
        ),
    )[:250]


def install_command(source: str, name: str) -> tuple[str, list[str]]:
    package = validate_package_name(name)
    if source == "apt":
        require_apt()
        return f"APT installs {package}", privileged(["apt-get", "install", "-y", package])
    if source == "dnf":
        dnf = dnf_binary()
        if not dnf:
            raise ApiError("dnf is not installed or not in PATH.", 404)
        return f"dnf installs {package}", privileged([dnf, "install", "-y", package])
    if source == "zypper":
        require_binary("zypper")
        return f"zypper installs {package}", privileged(["zypper", "--non-interactive", "install", package])
    if source == "pacman":
        require_binary("pacman")
        return f"Pacman installs {package}", privileged(["pacman", "-S", "--needed", "--noconfirm", package])
    if source == "aur":
        helper = aur_helper()
        if not helper:
            raise ApiError("Install yay or paru to install AUR packages.", 404)
        return f"AUR installs {package}", [helper, "-S", "--needed", "--noconfirm", *aur_sudo_options(), package]
    if source == "apk":
        require_binary("apk")
        return f"apk installs {package}", privileged(["apk", "add", package])
    if source == "xbps":
        require_binary("xbps-install")
        return f"xbps installs {package}", privileged(["xbps-install", "-Sy", package])
    if source == "eopkg":
        require_binary("eopkg")
        return f"eopkg installs {package}", privileged(["eopkg", "-y", "install", package])
    if source == "flatpak":
        require_binary("flatpak")
        return f"Flatpak installs {package}", ["flatpak", "install", "-y", "flathub", package]
    if source == "snap":
        require_binary("snap")
        return f"Snap installs {package}", privileged(["snap", "install", package])
    if source == "brew":
        require_binary("brew")
        return f"Homebrew installs {package}", ["brew", "install", package]
    if source == "npm":
        require_binary("npm")
        return f"npm installs {package}", ["npm", "install", "-g", package]
    if source == "pip":
        python = require_python_pip()
        return f"pip installs {package}", [python, "-m", "pip", "install", "--user", package]
    raise ApiError("Unknown source.", 404)


def uninstall_command(source: str, name: str) -> tuple[str, list[str]]:
    package = validate_package_name(name)
    if source == "apt":
        require_apt()
        return f"APT removes {package}", privileged(["apt-get", "purge", "-y", package])
    if source == "dnf":
        dnf = dnf_binary()
        if not dnf:
            raise ApiError("dnf is not installed or not in PATH.", 404)
        return f"dnf removes {package}", privileged([dnf, "remove", "-y", package])
    if source == "zypper":
        require_binary("zypper")
        return f"zypper removes {package}", privileged(["zypper", "--non-interactive", "remove", package])
    if source == "pacman":
        require_binary("pacman")
        return f"Pacman removes {package}", privileged(["pacman", "-Rns", "--noconfirm", package])
    if source == "aur":
        helper = aur_helper()
        if helper:
            return f"AUR removes {package}", [helper, "-Rns", "--noconfirm", *aur_sudo_options(), package]
        require_binary("pacman")
        return f"Pacman removes AUR package {package}", privileged(["pacman", "-Rns", "--noconfirm", package])
    if source == "apk":
        require_binary("apk")
        return f"apk removes {package}", privileged(["apk", "del", package])
    if source == "xbps":
        require_binary("xbps-remove")
        return f"xbps removes {package}", privileged(["xbps-remove", "-R", package])
    if source == "eopkg":
        require_binary("eopkg")
        return f"eopkg removes {package}", privileged(["eopkg", "-y", "remove", package])
    if source == "flatpak":
        require_binary("flatpak")
        return f"Flatpak removes {package}", ["flatpak", "uninstall", "-y", package]
    if source == "snap":
        require_binary("snap")
        return f"Snap removes {package}", privileged(["snap", "remove", package])
    if source == "brew":
        require_binary("brew")
        return f"Homebrew removes {package}", ["brew", "uninstall", package]
    if source == "npm":
        require_binary("npm")
        return f"npm removes {package}", ["npm", "uninstall", "-g", package]
    if source == "pip":
        python = require_python_pip()
        return f"pip removes {package}", [python, "-m", "pip", "uninstall", "-y", package]
    raise ApiError("Unknown source.", 404)


def start_job(label: str, command: list[str]) -> Job:
    job = Job(id=uuid.uuid4().hex[:12], label=label, command=command)
    with JOBS_LOCK:
        JOBS[job.id] = job
    thread = threading.Thread(target=run_job, args=(job.id,), daemon=True)
    thread.start()
    return job


def run_job(job_id: str) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        job.state = "running"
    try:
        proc = subprocess.Popen(
            job.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            with JOBS_LOCK:
                JOBS[job_id].output.append(line.rstrip("\n"))
        code = proc.wait()
        with JOBS_LOCK:
            JOBS[job_id].exit_code = code
            JOBS[job_id].state = "done" if code == 0 else "failed"
    except FileNotFoundError:
        with JOBS_LOCK:
            JOBS[job_id].state = "failed"
            JOBS[job_id].exit_code = 127
            JOBS[job_id].output.append("Command was not found.")
    except Exception as exc:  # noqa: BLE001 - API boundary
        with JOBS_LOCK:
            JOBS[job_id].state = "failed"
            JOBS[job_id].exit_code = 1
            JOBS[job_id].output.append(str(exc))


def job_to_dict(job: Job) -> dict[str, Any]:
    return {
        "id": job.id,
        "label": job.label,
        "command": job.command,
        "createdAt": int(job.created_at * 1000),
        "state": job.state,
        "exitCode": job.exit_code,
        "output": job.output[-500:],
    }


def install_appimage(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    source_path = safe_path(str(payload.get("appimagePath", "")))
    if source_path.suffix.lower() != ".appimage":
        raise ApiError("File must be an .AppImage file.")
    slug = slugify(name or source_path.stem)
    APPIMAGE_DIR.mkdir(parents=True, exist_ok=True)
    target = APPIMAGE_DIR / f"{slug}.AppImage"
    shutil.copy2(source_path, target)
    target.chmod(target.stat().st_mode | 0o111)
    icon_value = str(payload.get("iconPath", "")).strip()
    icon_path = safe_path(icon_value) if icon_value else None
    copied_icon = copy_icon(icon_path, slug)
    desktop_path = create_desktop_file(slug, name or source_path.stem, target, copied_icon)
    entry = register_manual(
        {
            "id": slug,
            "kind": "AppImage",
            "name": name or source_path.stem,
            "version": "",
            "path": str(target),
            "desktop": desktop_path,
            "icon": copied_icon,
            "installedAt": now_ms(),
        }
    )
    return entry


def install_archive(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    archive_path = safe_path(str(payload.get("archivePath", "")))
    slug = slugify(name or archive_path.stem)
    target = ARCHIVE_DIR / slug
    if target.exists():
        shutil.rmtree(target)
    suffixes = "".join(archive_path.suffixes).lower()
    if suffixes.endswith((".tar.gz", ".tgz", ".tar.xz", ".txz", ".tar.bz2", ".tbz2", ".tar")):
        safe_extract_tar(archive_path, target)
    elif archive_path.suffix.lower() == ".zip":
        safe_extract_zip(archive_path, target)
    else:
        raise ApiError("Supported formats are .tar, .tar.gz, .tar.xz, .tar.bz2, .tgz, .txz, .tbz2 and .zip.")

    executable_rel = str(payload.get("executable", "")).strip().lstrip("/")
    exec_path = None
    desktop_path = None
    icon_value = str(payload.get("iconPath", "")).strip()
    icon_path = safe_path(icon_value) if icon_value else None
    copied_icon = copy_icon(icon_path, slug)
    symlink = None
    if executable_rel:
        candidate = (target / executable_rel).resolve()
        if target.resolve() not in candidate.parents and candidate != target.resolve():
            raise ApiError("Executable must be inside the extracted folder.")
        if not candidate.exists():
            raise ApiError("Executable was not found in the extracted archive target.", 404)
        candidate.chmod(candidate.stat().st_mode | 0o111)
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        symlink_path = BIN_DIR / slug
        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()
        symlink_path.symlink_to(candidate)
        exec_path = candidate
        symlink = str(symlink_path)
        desktop_path = create_desktop_file(slug, name or archive_path.stem, candidate, copied_icon)

    entry = register_manual(
        {
            "id": slug,
            "kind": "Archive",
            "name": name or archive_path.stem,
            "version": "",
            "path": str(target),
            "desktop": desktop_path,
            "icon": copied_icon,
            "symlink": symlink,
            "executable": str(exec_path) if exec_path else None,
            "installedAt": now_ms(),
        }
    )
    return entry


def uninstall_manual(identifier: str) -> dict[str, Any]:
    identifier = slugify(identifier)
    entry = remove_registry_entry(identifier)
    for key in ("desktop", "icon", "symlink"):
        value = entry.get(key)
        if value:
            path = Path(value).expanduser()
            try:
                if path.exists() or path.is_symlink():
                    path.unlink()
            except OSError:
                pass
    app_path = Path(str(entry.get("path", ""))).expanduser()
    managed_roots = [APPIMAGE_DIR.resolve(), ARCHIVE_DIR.resolve(), LEGACY_APPIMAGE_DIR.resolve(), LEGACY_ARCHIVE_DIR.resolve()]
    try:
        resolved = app_path.resolve()
        if any(root == resolved or root in resolved.parents for root in managed_roots):
            if resolved.is_dir():
                shutil.rmtree(resolved)
            elif resolved.exists():
                resolved.unlink()
    except OSError:
        pass
    return entry


def status() -> dict[str, Any]:
    pacman_repos: list[str] = []
    if which("pacman-conf"):
        code, output = run_capture(["pacman-conf", "--repo-list"])
        if code == 0:
            pacman_repos = [line.strip() for line in output.splitlines() if line.strip()]
    helper = aur_helper()
    python = python_executable()
    pip_ready = False
    if python:
        pip_ready = run_capture([python, "-m", "pip", "--version"])[0] == 0
    return {
        "app": APP_NAME,
        "paths": {
            "registry": str(REGISTRY_PATH),
            "appimages": str(APPIMAGE_DIR),
            "archives": str(ARCHIVE_DIR),
            "desktopFiles": str(APPLICATIONS_DIR),
        },
        "sources": {
            "apt": {
                "available": apt_available(),
                "detail": which("apt-cache") or "apt-cache missing",
            },
            "dnf": {"available": bool(dnf_binary()), "detail": dnf_binary() or "dnf missing"},
            "zypper": {"available": zypper_available(), "detail": which("zypper") or "zypper missing"},
            "pacman": {"available": bool(which("pacman")), "detail": ", ".join(pacman_repos) or "pacman"},
            "aur": {"available": bool(helper), "detail": helper or "yay/paru missing"},
            "apk": {"available": apk_available(), "detail": which("apk") or "apk missing"},
            "xbps": {"available": xbps_available(), "detail": which("xbps-query") or "xbps missing"},
            "eopkg": {"available": eopkg_available(), "detail": which("eopkg") or "eopkg missing"},
            "flatpak": {"available": bool(which("flatpak")), "detail": which("flatpak") or "flatpak missing"},
            "snap": {"available": bool(which("snap")), "detail": which("snap") or "snap missing"},
            "brew": {"available": bool(which("brew")), "detail": which("brew") or "brew missing"},
            "npm": {"available": bool(which("npm")), "detail": which("npm") or "npm missing"},
            "pip": {"available": pip_ready, "detail": f"{python} -m pip" if pip_ready else "python3/pip missing"},
            "manual": {"available": True, "detail": str(CONFIG_DIR)},
        },
    }


def list_installed(source: str | None) -> list[dict[str, Any]]:
    mapping = {
        "apt": list_apt_installed,
        "dnf": lambda: list_rpm_installed("dnf"),
        "zypper": lambda: list_rpm_installed("zypper"),
        "pacman": lambda: list_pacman_installed(False),
        "aur": lambda: list_pacman_installed(True),
        "apk": list_apk_installed,
        "xbps": list_xbps_installed,
        "eopkg": list_eopkg_installed,
        "flatpak": list_flatpak_installed,
        "snap": list_snap_installed,
        "brew": list_brew_installed,
        "npm": list_npm_installed,
        "pip": list_pip_installed,
        "manual": list_manual_installed,
        "desktop": list_desktop_installed,
    }
    if source and source != "all":
        if source not in mapping:
            raise ApiError("Unknown source.", 404)
        desktop_index = desktop_package_index()
        return [enrich_item(item, desktop_index) for item in mapping[source]()]
    items: list[dict[str, Any]] = []
    for source_id, getter in mapping.items():
        if source_id == "desktop":
            continue
        items.extend(getter())
    desktop_index = desktop_package_index()
    items = [enrich_item(item, desktop_index) for item in items]
    return sorted(items, key=lambda item: (item.get("source", ""), item.get("name", "").lower()))


class Handler(BaseHTTPRequestHandler):
    server_version = "OmniPkg/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            path = unquote(parsed.path)
            if path.startswith("/api/"):
                self.handle_api_get(path, parse_qs(parsed.query))
                return
            self.serve_static(path)
        except ApiError as exc:
            self.send_json({"error": exc.message}, exc.status)
        except Exception as exc:  # noqa: BLE001 - API boundary
            self.send_json({"error": str(exc)}, 500)

    def do_POST(self) -> None:
        try:
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(raw or "{}")
            self.handle_api_post(parsed.path, payload)
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON."}, 400)
        except ApiError as exc:
            self.send_json({"error": exc.message}, exc.status)
        except Exception as exc:  # noqa: BLE001 - API boundary
            self.send_json({"error": str(exc)}, 500)

    def handle_api_get(self, path: str, query: dict[str, list[str]]) -> None:
        if path == "/api/status":
            self.send_json(status())
            return
        if path == "/api/installed":
            source = query.get("source", ["all"])[0]
            self.send_json({"items": list_installed(source)})
            return
        if path == "/api/search":
            source = query.get("source", ["pacman"])[0]
            term = query.get("q", [""])[0]
            self.send_json({"items": search_packages(source, term)})
            return
        if path == "/api/jobs":
            with JOBS_LOCK:
                jobs = [job_to_dict(job) for job in sorted(JOBS.values(), key=lambda item: item.created_at, reverse=True)]
            self.send_json({"items": jobs[:20]})
            return
        match = re.match(r"^/api/jobs/([A-Za-z0-9]+)$", path)
        if match:
            with JOBS_LOCK:
                job = JOBS.get(match.group(1))
                if not job:
                    raise ApiError("Job was not found.", 404)
                self.send_json(job_to_dict(job))
            return
        raise ApiError("API endpoint was not found.", 404)

    def handle_api_post(self, path: str, payload: dict[str, Any]) -> None:
        if path == "/api/install":
            label, command = install_command(str(payload.get("source", "")), str(payload.get("name", "")))
            self.send_json({"job": job_to_dict(start_job(label, command))})
            return
        if path == "/api/uninstall":
            source = str(payload.get("source", ""))
            if source == "manual":
                entry = uninstall_manual(str(payload.get("id") or payload.get("name") or ""))
                self.send_json({"removed": entry})
                return
            label, command = uninstall_command(source, str(payload.get("name", "")))
            self.send_json({"job": job_to_dict(start_job(label, command))})
            return
        if path == "/api/manual/appimage":
            self.send_json({"entry": install_appimage(payload)})
            return
        if path == "/api/manual/archive":
            self.send_json({"entry": install_archive(payload)})
            return
        raise ApiError("API endpoint was not found.", 404)

    def serve_static(self, path: str) -> None:
        if path in ("", "/"):
            target = WEB_ROOT / "index.html"
        else:
            target = (WEB_ROOT / path.lstrip("/")).resolve()
            if WEB_ROOT.resolve() not in target.parents and target != WEB_ROOT.resolve():
                raise ApiError("Path outside the app.", 403)
        if not target.exists() or target.is_dir():
            raise ApiError("File was not found.", 404)
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml",
        }
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_types.get(target.suffix, "application/octet-stream"))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(target.read_bytes())

    def send_json(self, data: Any, status_code: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=True).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    WEB_ROOT.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((HOST, args.port), Handler)
    print(f"{APP_NAME} is running at http://{HOST}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
