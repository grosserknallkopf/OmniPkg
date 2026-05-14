#!/usr/bin/env python3
"""Native GTK desktop shell for OmniPkg."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

import omnipkg_core as core  # noqa: E402


APP_ID = "dev.omnipkg.omnipkg"
APP_TITLE = "OmniPkg"
ROOT = Path(__file__).resolve().parent
ICON_SOURCE = ROOT / "assets" / "omnipkg-logo.png"
ASKPASS_SCRIPT = ROOT / "assets" / "omnipkg-askpass.py"
MENU_ICON = Path.home() / ".local" / "share" / "icons" / "hicolor" / "512x512" / "apps" / "omnipkg.png"
PIXMAP_ICON = Path.home() / ".local" / "share" / "pixmaps" / "omnipkg.png"
DESKTOP_FILE = Path.home() / ".local" / "share" / "applications" / f"{APP_ID}.desktop"
LEGACY_DESKTOP_FILES = (
    Path.home() / ".local" / "share" / "applications" / "omnipkg.desktop",
    Path.home() / ".local" / "share" / "applications" / "arch-software-manager.desktop",
)
BIN_FILE = Path.home() / ".local" / "bin" / "omnipkg"
LEGACY_APP_DIR = Path.home() / ".local" / "share" / "arch-software-manager"
LEGACY_BIN_FILES = (
    Path.home() / ".local" / "bin" / "arch-software-manager",
    Path.home() / ".local" / "bin" / "arch_software_manager",
)
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256, 512)

SOURCES = [
    ("apt", "APT"),
    ("dnf", "DNF"),
    ("zypper", "Zypper"),
    ("pacman", "Pacman"),
    ("aur", "AUR"),
    ("apk", "APK"),
    ("xbps", "XBPS"),
    ("eopkg", "eopkg"),
    ("flatpak", "Flatpak"),
    ("snap", "Snap"),
    ("brew", "Homebrew"),
    ("npm", "npm"),
    ("pip", "pipx"),
]

TRANSLATIONS = {
    "en": {
        "admin_already_root": "The app is already running with root privileges.",
        "admin_authorized": "Admin authorization prepared.",
        "admin_not_confirmed": "Admin authorization was not confirmed. System packages will ask again later.",
        "admin_prepare": "Preparing admin authorization...",
        "admin_sudo_authorized": "Sudo authorization prepared.",
        "admin_sudo_not_confirmed": "Sudo authorization was not confirmed. System packages will ask again later.",
        "appimage_file": "AppImage file",
        "appimage_failed": "AppImage failed: {error}",
        "appimage_installed": "{name} installed",
        "apps_only": "Apps only",
        "archive": "Archive",
        "archive_failed": "Archive failed: {error}",
        "archive_file": "Archive file",
        "archive_installed": "{name} installed",
        "add_source": "Add source",
        "add_source_failed": "Adding source failed: {error}",
        "add_source_started": "Adding source: {name}",
        "all_packages": "All packages",
        "components": "Components",
        "cancel": "Cancel",
        "choose": "Choose",
        "choose_file": "Choose a file",
        "close": "Close",
        "desktop_launcher_logo": "Desktop launcher logo",
        "discover": "Discover",
        "distribution": "Distribution",
        "empty_discover": "Search for software. OmniPkg will look across every available source.",
        "entries_count": "{count} of {total} entries",
        "error_details": "Error details",
        "executable_inside_archive": "Executable inside archive",
        "frontend": "Frontend",
        "frontend_auto": "Automatic",
        "frontend_gtk": "GTK",
        "frontend_qt": "Qt",
        "frontend_restart": "Frontend preference saved. Restart OmniPkg to apply it.",
        "install": "Install",
        "install_appimage": "Install AppImage",
        "install_archive": "Install archive",
        "install_manager": "Install package managers",
        "install_manager_failed": "Package manager installation failed: {error}",
        "install_manager_missing_after": "{name} installation finished, but OmniPkg still cannot find it.",
        "install_manager_started": "Installing package manager: {name}",
        "install_missing_manager_prompt": "{name} is not installed. Install it now?",
        "install_missing_manager_chip": "{name}: missing. install?",
        "installing_manager_chip": "{name}: installing...",
        "installing_now": "Installing...",
        "installed": "Installed",
        "installed_load_failed": "Installed packages could not be loaded.",
        "installed_load_failed_log": "Installed packages could not be loaded: {error}",
        "installed_state": "Installed",
        "job_not_found": "Job not found.",
        "job_failed": "{label} failed ({code})",
        "job_started": "Job started: {job_id}",
        "key_url": "Signing key URL",
        "language": "Language",
        "loading_installed": "Loading installed packages...",
        "manual": "Manual",
        "manual_install": "Manual install",
        "manager": "Manager",
        "min_chars": "Please enter at least two characters.",
        "missing": "missing",
        "mode_all": "all packages",
        "mode_gui": "graphical apps",
        "native_source": "System package sources",
        "no_installed": "No installed entries found.",
        "no_job_output": "The package manager did not return any additional output.",
        "no_results": "No results in the available sources.",
        "no_updates": "No updates found.",
        "no_updates_filtered": "No updates match the current search or filter.",
        "no": "No",
        "pkexec_missing": "pkexec is missing. Install polkit/pkexec for graphical admin prompts.",
        "sudo_askpass_unsupported": "pkexec is missing and this sudo does not support askpass (-A). Install polkit/pkexec or a sudo build with askpass support.",
        "ready": "ready",
        "refresh": "Refresh",
        "remove": "Remove",
        "removing_now": "Removing...",
        "removed": "{name} removed",
        "removal_failed": "Removal failed: {error}",
        "search": "Search",
        "search_failed": "Search failed: {error}",
        "search_finished": "Search finished: {count} results",
        "search_placeholder": "Search apps, packages, AppImages, CLI tools or libraries",
        "search_results": "Search results for \"{query}\"",
        "search_started": "Search started: {query} ({mode})",
        "searching": "OmniPkg is searching {mode} across all available sources...",
        "source_name": "Source name",
        "source_url": "Repository URL",
        "source_status_failed": "Source status failed: {error}",
        "tagline": "One roof for all your package sources",
        "title": "OmniPkg",
        "unknown_admin": "Neither pkexec nor sudo was found. System-wide installs cannot start.",
        "update": "Update",
        "update_all": "Update all",
        "update_failed": "Update failed: {error}",
        "update_started": "Update started: {source}",
        "updating_now": "Updating...",
        "updates_check_failed": "Updates could not be checked: {error}",
        "updates_found": "{count} updates available",
        "checking_updates": "Checking for updates...",
        "updates": "Updates",
        "yes": "Yes",
    },
    "de": {
        "admin_already_root": "Die App läuft bereits mit Root-Rechten.",
        "admin_authorized": "Admin-Freigabe ist vorbereitet.",
        "admin_not_confirmed": "Admin-Freigabe wurde nicht bestätigt. Systempakete fragen später erneut nach.",
        "admin_prepare": "Admin-Freigabe wird vorbereitet...",
        "admin_sudo_authorized": "Sudo-Freigabe ist vorbereitet.",
        "admin_sudo_not_confirmed": "Sudo-Freigabe wurde nicht bestätigt. Systempakete fragen später erneut nach.",
        "appimage_file": "AppImage-Datei",
        "appimage_failed": "AppImage fehlgeschlagen: {error}",
        "appimage_installed": "{name} installiert",
        "apps_only": "Nur Apps",
        "archive": "Archiv",
        "archive_failed": "Archiv fehlgeschlagen: {error}",
        "archive_file": "Archivdatei",
        "archive_installed": "{name} installiert",
        "add_source": "Quelle hinzufügen",
        "add_source_failed": "Quelle konnte nicht hinzugefügt werden: {error}",
        "add_source_started": "Quelle wird hinzugefügt: {name}",
        "all_packages": "Alle Pakete",
        "components": "Komponenten",
        "cancel": "Abbrechen",
        "choose": "Auswählen",
        "choose_file": "Datei auswählen",
        "close": "Schließen",
        "desktop_launcher_logo": "Logo für Anwendungsmenü",
        "discover": "Entdecken",
        "distribution": "Distribution",
        "empty_discover": "Suche nach Software. OmniPkg durchsucht jede verfügbare Quelle.",
        "entries_count": "{count} von {total} Einträgen",
        "error_details": "Fehlerdetails",
        "executable_inside_archive": "Programmdatei im Archiv",
        "frontend": "Frontend",
        "frontend_auto": "Automatisch",
        "frontend_gtk": "GTK",
        "frontend_qt": "Qt",
        "frontend_restart": "Frontend-Einstellung gespeichert. Starte OmniPkg neu, um sie zu übernehmen.",
        "install": "Installieren",
        "install_appimage": "AppImage installieren",
        "install_archive": "Archiv installieren",
        "install_manager": "Paketmanager installieren",
        "install_manager_failed": "Paketmanager-Installation fehlgeschlagen: {error}",
        "install_manager_missing_after": "{name}-Installation ist beendet, aber OmniPkg findet den Paketmanager noch nicht.",
        "install_manager_started": "Paketmanager wird installiert: {name}",
        "install_missing_manager_prompt": "{name} ist nicht installiert. Jetzt installieren?",
        "install_missing_manager_chip": "{name}: fehlt. installieren?",
        "installing_manager_chip": "{name}: wird installiert...",
        "installing_now": "Wird installiert...",
        "installed": "Installiert",
        "installed_load_failed": "Installierte Pakete konnten nicht geladen werden.",
        "installed_load_failed_log": "Installierte Pakete konnten nicht geladen werden: {error}",
        "installed_state": "Installiert",
        "job_not_found": "Aufgabe nicht gefunden.",
        "job_failed": "{label} fehlgeschlagen ({code})",
        "job_started": "Aufgabe gestartet: {job_id}",
        "key_url": "URL des Signaturschlüssels",
        "language": "Sprache",
        "loading_installed": "Installierte Pakete werden geladen...",
        "manual": "Manuell",
        "manual_install": "Manuell installieren",
        "manager": "Manager",
        "min_chars": "Bitte mindestens zwei Zeichen eingeben.",
        "missing": "fehlt",
        "mode_all": "allen Paketen",
        "mode_gui": "grafischen Apps",
        "native_source": "System-Paketquellen",
        "no_installed": "Keine installierten Einträge gefunden.",
        "no_job_output": "Der Paketmanager hat keine weiteren Details ausgegeben.",
        "no_results": "Keine Treffer in den verfügbaren Quellen.",
        "no_updates": "Keine Updates gefunden.",
        "no_updates_filtered": "Keine Updates passen zur aktuellen Suche oder zum Filter.",
        "no": "Nein",
        "pkexec_missing": "pkexec fehlt. Installiere polkit/pkexec für grafische Admin-Abfragen.",
        "sudo_askpass_unsupported": "pkexec fehlt und dieses sudo unterstützt kein Askpass (-A). Installiere polkit/pkexec oder ein sudo mit Askpass-Unterstützung.",
        "ready": "bereit",
        "refresh": "Aktualisieren",
        "remove": "Deinstallieren",
        "removing_now": "Wird deinstalliert",
        "removed": "{name} entfernt",
        "removal_failed": "Entfernen fehlgeschlagen: {error}",
        "search": "Suchen",
        "search_failed": "Suche fehlgeschlagen: {error}",
        "search_finished": "Suche abgeschlossen: {count} Treffer",
        "search_placeholder": "Apps, Pakete, AppImages, CLI-Tools oder Bibliotheken suchen",
        "search_results": "Suchergebnisse für \"{query}\"",
        "search_started": "Suche gestartet: {query} ({mode})",
        "searching": "OmniPkg sucht nach {mode} in allen verfügbaren Quellen...",
        "source_name": "Quellenname",
        "source_url": "Repository-URL",
        "source_status_failed": "Quellenstatus fehlgeschlagen: {error}",
        "tagline": "Ein Dach für alle Paketquellen",
        "title": "OmniPkg",
        "unknown_admin": "Weder pkexec noch sudo wurde gefunden. Systemweite Installationen können nicht starten.",
        "update": "Aktualisieren",
        "update_all": "Alle aktualisieren",
        "update_failed": "Aktualisierung fehlgeschlagen: {error}",
        "update_started": "Aktualisierung gestartet: {source}",
        "updating_now": "Wird aktualisiert...",
        "updates_check_failed": "Updates konnten nicht geprüft werden: {error}",
        "updates_found": "{count} Updates verfügbar",
        "checking_updates": "Updates werden gesucht...",
        "updates": "Updates",
        "yes": "Ja",
    },
}


def detect_language() -> str:
    override = os.environ.get("OMNIPKG_LANG", "").strip().lower()
    if override.startswith(("de", "en")):
        return override[:2]
    candidates = (
        os.environ.get("LANGUAGE", ""),
        os.environ.get("LANG", ""),
        os.environ.get("LC_MESSAGES", ""),
        os.environ.get("LC_ALL", ""),
    )
    for value in candidates:
        primary = value.split(":", 1)[0].split(".", 1)[0].replace("_", "-").lower()
        if primary.startswith("de"):
            return "de"
    return "en"


LANGUAGE = detect_language()


def set_language(language: str) -> None:
    global LANGUAGE
    LANGUAGE = "de" if language == "de" else "en"
    os.environ["OMNIPKG_LANG"] = LANGUAGE


def tr(key: str, **values: Any) -> str:
    text = TRANSLATIONS.get(LANGUAGE, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))
    return text.format(**values) if values else text

CSS = """
window {
  background: #f6f4ef;
  color: #1d2528;
  font-family: Inter, Cantarell, Sans-Serif;
}

.root {
  background: #f6f4ef;
}

.main {
  padding: 22px 24px 24px;
}

.brand-mark {
  border-radius: 8px;
  min-width: 58px;
  min-height: 54px;
}

.brand-title {
  font-size: 20px;
  font-weight: 900;
}

.brand-subtitle,
.muted {
  color: #687477;
}

.search-entry {
  min-height: 52px;
  border-radius: 8px;
  border: 1px solid #d8d2c6;
  background: #fffdf8;
  box-shadow: 0 8px 20px rgba(31,37,39,.05);
  padding: 0 12px;
  font-size: 16px;
}

.tabs {
  background: #ece7dc;
  border: 1px solid #d8d2c6;
  border-radius: 8px;
  padding: 4px;
}

.tab-button {
  min-height: 42px;
  border-radius: 6px;
  padding: 0 16px;
  font-weight: 800;
  color: #687477;
  background: transparent;
}

.tab-button.active {
  background: #fffdf8;
  color: #1d2528;
  box-shadow: 0 4px 13px rgba(31,37,39,.08);
}

.primary {
  background: #0f766e;
  color: #f8fffd;
  border-radius: 8px;
  min-height: 42px;
  padding: 0 16px;
  font-weight: 900;
}

.secondary {
  background: #e8eef4;
  color: #285f9f;
  border-radius: 8px;
  min-height: 40px;
  padding: 0 14px;
  font-weight: 800;
}

.danger {
  background: #f4e2df;
  color: #b13d35;
  border-radius: 8px;
  min-height: 40px;
  padding: 0 14px;
  font-weight: 800;
}

.chip {
  background: #fffdf8;
  border: 1px solid #d8d2c6;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 800;
  color: #445053;
}

.chip.off {
  color: #916012;
  background: #fbefd8;
}

.section-title {
  font-size: 34px;
  font-weight: 900;
}

.package-row {
  background: #fffdf8;
  border: 1px solid #d8d2c6;
  border-radius: 8px;
  margin: 5px 0;
  padding: 13px;
  box-shadow: 0 7px 17px rgba(31,37,39,.05);
}

.package-icon {
  background: #e0f2ef;
  color: #0b4f49;
  border-radius: 8px;
  min-width: 46px;
  min-height: 46px;
  font-weight: 900;
}

.package-icon image {
  color: #0b4f49;
}

.package-name {
  font-size: 15px;
  font-weight: 900;
}

.source-badge {
  color: #b7791f;
  font-size: 12px;
  font-weight: 900;
}

.tool-panel {
  background: #fffdf8;
  border: 1px solid #d8d2c6;
  border-radius: 8px;
  padding: 18px;
  box-shadow: 0 18px 45px rgba(31,37,39,.12);
}

.panel-title {
  font-size: 18px;
  font-weight: 900;
}

.status-ok {
  color: #0f766e;
  font-weight: 900;
}

.field-label {
  color: #687477;
  font-size: 13px;
  font-weight: 800;
}

.field-entry {
  min-height: 42px;
  border-radius: 8px;
  border: 1px solid #d8d2c6;
  background: #fbfaf6;
}

.empty {
  color: #687477;
  padding: 32px;
}
"""


def run_in_thread(fn: Callable[[], Any], on_done: Callable[[Any, Exception | None], None]) -> None:
    def worker() -> None:
        try:
            result = fn()
            GLib.idle_add(on_done, result, None)
        except Exception as exc:  # noqa: BLE001 - UI boundary
            GLib.idle_add(on_done, None, exc)

    threading.Thread(target=worker, daemon=True).start()


def DATA_HOME_ICON_DIR(size: int) -> Path:
    return Path.home() / ".local" / "share" / "icons" / "hicolor" / f"{size}x{size}" / "apps"


def install_launcher() -> None:
    MENU_ICON.parent.mkdir(parents=True, exist_ok=True)
    PIXMAP_ICON.parent.mkdir(parents=True, exist_ok=True)
    DESKTOP_FILE.parent.mkdir(parents=True, exist_ok=True)
    if ICON_SOURCE.exists():
        MENU_ICON.write_bytes(ICON_SOURCE.read_bytes())
        PIXMAP_ICON.write_bytes(ICON_SOURCE.read_bytes())
        converter = core.which("magick") or core.which("convert")
        for size in ICON_SIZES:
            target = DATA_HOME_ICON_DIR(size) / "omnipkg.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            if converter:
                subprocess.run(
                    [
                        converter,
                        str(ICON_SOURCE),
                        "-resize",
                        f"{size}x{size}",
                        "-background",
                        "none",
                        "-gravity",
                        "center",
                        "-extent",
                        f"{size}x{size}",
                        str(target),
                    ],
                    check=False,
                )
            elif size == 512:
                target.write_bytes(ICON_SOURCE.read_bytes())
        if core.which("xdg-icon-resource"):
            for size in ICON_SIZES:
                target = DATA_HOME_ICON_DIR(size) / "omnipkg.png"
                if target.exists():
                    subprocess.run(
                        ["xdg-icon-resource", "install", "--noupdate", "--novendor", "--mode", "user", "--size", str(size), str(target), "omnipkg"],
                        check=False,
                    )
            subprocess.run(["xdg-icon-resource", "forceupdate", "--mode", "user"], check=False)
    if ASKPASS_SCRIPT.exists():
        ASKPASS_SCRIPT.chmod(0o755)
    BIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    BIN_FILE.write_text(
        "#!/usr/bin/env sh\n"
        'LOG_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/omnipkg"\n'
        'mkdir -p "$LOG_DIR"\n'
        f'cd "{ROOT}" || exit 1\n'
        f'exec python3 "{ROOT / "omnipkg.py"}" "$@" >> "$LOG_DIR/omnipkg.log" 2>&1\n',
        encoding="utf-8",
    )
    BIN_FILE.chmod(0o755)
    for legacy_file in LEGACY_DESKTOP_FILES:
        if legacy_file.exists():
            legacy_file.unlink()
    for legacy_bin in LEGACY_BIN_FILES:
        if legacy_bin.exists():
            legacy_bin.unlink()
    if LEGACY_APP_DIR.exists():
        shutil.rmtree(LEGACY_APP_DIR, ignore_errors=True)
    desktop = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=OmniPkg\n"
        "Comment=Install and manage apps from APT, DNF, Zypper, Pacman, AUR, APK, XBPS, eopkg, Flatpak, Snap, Homebrew, npm, pipx and AppImages\n"
        f"Exec={BIN_FILE}\n"
        "Icon=omnipkg\n"
        "Terminal=false\n"
        "Categories=Settings;PackageManager;\n"
        f"StartupWMClass={APP_ID}\n"
        "StartupNotify=false\n"
    )
    DESKTOP_FILE.write_text(desktop, encoding="utf-8")
    DESKTOP_FILE.chmod(0o755)
    if core.which("xdg-desktop-menu"):
        subprocess.run(["xdg-desktop-menu", "forceupdate"], check=False)
    subprocess.run(["update-desktop-database", str(DESKTOP_FILE.parent)], check=False)
    icon_theme_root = MENU_ICON.parents[2]
    if (icon_theme_root / "index.theme").exists():
        subprocess.run(["gtk-update-icon-cache", "-q", str(icon_theme_root)], check=False)


def icon_widget(item: dict[str, Any], fallback: str = "?") -> Gtk.Widget:
    frame = Gtk.Box()
    frame.add_css_class("package-icon")
    frame.set_halign(Gtk.Align.CENTER)
    frame.set_valign(Gtk.Align.CENTER)
    icon = str(item.get("icon", "") or "").strip()
    image: Gtk.Image | None = None
    if icon:
        icon_path = Path(icon).expanduser()
        if icon_path.exists():
            image = Gtk.Image.new_from_file(str(icon_path))
        else:
            icon_name = re.sub(r"\.(png|svg|webp|jpg|jpeg)$", "", icon, flags=re.IGNORECASE)
            image = Gtk.Image.new_from_icon_name(icon_name)
    if image:
        image.set_pixel_size(34)
        frame.append(image)
    else:
        label = Gtk.Label(label=fallback[:1].upper())
        frame.append(label)
    return frame


class PackageRow(Gtk.ListBoxRow):
    def __init__(self, item: dict[str, Any], action_label: str, action_class: str, callback: Callable[[dict[str, Any], "PackageRow"], None]):
        super().__init__()
        self.item = item
        self.add_css_class("package-row")
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=13)
        box.set_valign(Gtk.Align.CENTER)
        self.set_child(box)

        box.append(icon_widget(item, item.get("source", "?")))

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        text_box.set_hexpand(True)
        box.append(text_box)

        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        text_box.append(title_box)

        name = Gtk.Label(label=item.get("name") or item.get("id") or "Untitled")
        name.set_xalign(0)
        name.set_ellipsize(3)
        name.add_css_class("package-name")
        title_box.append(name)

        badge = Gtk.Label(label=item.get("source", "").upper())
        badge.add_css_class("source-badge")
        title_box.append(badge)

        description = Gtk.Label(label=item.get("description") or item.get("path") or item.get("origin") or "")
        description.set_xalign(0)
        description.set_ellipsize(3)
        description.add_css_class("muted")
        text_box.append(description)

        package_name = item.get("packageName") if item.get("packageName") != item.get("name") else ""
        detail = " · ".join(str(value) for value in (package_name, item.get("repo"), item.get("version"), item.get("kind")) if value)
        meta = Gtk.Label(label=detail)
        meta.set_xalign(0)
        meta.add_css_class("muted")
        text_box.append(meta)

        self.action_button = Gtk.Button(label=action_label)
        self.action_button.add_css_class(action_class)
        self.action_button.connect("clicked", lambda _button: callback(item, self))
        box.append(self.action_button)

        self.busy_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.busy_spinner = Gtk.Spinner()
        self.busy_label = Gtk.Label(label="")
        self.busy_box.append(self.busy_spinner)
        self.busy_box.append(self.busy_label)
        self.busy_box.set_visible(False)
        box.append(self.busy_box)

    def set_busy(self, text: str) -> None:
        self.action_button.set_sensitive(False)
        self.action_button.set_visible(False)
        self.busy_label.set_text(text)
        self.busy_spinner.start()
        self.busy_box.set_visible(True)

    def clear_busy(self) -> None:
        self.busy_spinner.stop()
        self.busy_box.set_visible(False)
        self.action_button.set_visible(True)
        self.action_button.set_sensitive(True)


class ActionRow(Gtk.ListBoxRow):
    def __init__(
        self,
        title: str,
        detail: str,
        action_label: str,
        action_class: str,
        callback: Callable[["ActionRow"], None],
        disabled: bool = False,
    ):
        super().__init__()
        self.add_css_class("package-row")
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_valign(Gtk.Align.CENTER)
        self.set_child(box)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        text_box.set_hexpand(True)
        box.append(text_box)
        title_label = Gtk.Label(label=title)
        title_label.set_xalign(0)
        title_label.add_css_class("package-name")
        text_box.append(title_label)
        detail_label = Gtk.Label(label=detail)
        detail_label.set_xalign(0)
        detail_label.set_wrap(True)
        detail_label.add_css_class("muted")
        text_box.append(detail_label)

        self.action_button = Gtk.Button(label=action_label)
        self.action_button.add_css_class(action_class)
        self.action_button.set_sensitive(not disabled)
        self.action_button.connect("clicked", lambda _button: callback(self))
        box.append(self.action_button)

        self.busy_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.busy_spinner = Gtk.Spinner()
        self.busy_label = Gtk.Label(label="")
        self.busy_box.append(self.busy_spinner)
        self.busy_box.append(self.busy_label)
        self.busy_box.set_visible(False)
        box.append(self.busy_box)

    def set_busy(self, text: str) -> None:
        self.action_button.set_visible(False)
        self.busy_label.set_text(text)
        self.busy_spinner.start()
        self.busy_box.set_visible(True)

    def clear_busy(self) -> None:
        self.busy_spinner.stop()
        self.busy_box.set_visible(False)
        self.action_button.set_visible(True)
        self.action_button.set_sensitive(True)


class PathField(Gtk.Box):
    def __init__(self, label: str, placeholder: str, window: Gtk.Window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.window = window
        field_label = Gtk.Label(label=label)
        field_label.set_xalign(0)
        field_label.add_css_class("field-label")
        self.append(field_label)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.append(row)
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text(placeholder)
        self.entry.add_css_class("field-entry")
        self.entry.set_hexpand(True)
        row.append(self.entry)

        choose = Gtk.Button(label="...")
        choose.add_css_class("secondary")
        choose.connect("clicked", self.choose_file)
        row.append(choose)

    def choose_file(self, _button: Gtk.Button) -> None:
        dialog = Gtk.FileChooserNative(
            title=tr("choose_file"),
            transient_for=self.window,
            action=Gtk.FileChooserAction.OPEN,
            accept_label=tr("choose"),
            cancel_label=tr("cancel"),
        )

        def response(native: Gtk.FileChooserNative, result: int) -> None:
            if result == Gtk.ResponseType.ACCEPT:
                file = native.get_file()
                if file and file.get_path():
                    self.entry.set_text(file.get_path() or "")
            native.destroy()

        dialog.connect("response", response)
        dialog.show()

    def get_text(self) -> str:
        return self.entry.get_text().strip()


class TextField(Gtk.Box):
    def __init__(self, label: str, placeholder: str):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        field_label = Gtk.Label(label=label)
        field_label.set_xalign(0)
        field_label.add_css_class("field-label")
        self.append(field_label)
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text(placeholder)
        self.entry.add_css_class("field-entry")
        self.append(self.entry)

    def get_text(self) -> str:
        return self.entry.get_text().strip()

    def clear(self) -> None:
        self.entry.set_text("")


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application, skip_admin: bool = False):
        super().__init__(application=app, title=APP_TITLE)
        self.set_default_size(1280, 780)
        self.status_data: dict[str, Any] | None = None
        self.current_view = "discover"
        self.results: list[dict[str, Any]] = []
        self.installed: list[dict[str, Any]] = []
        self.updates: list[dict[str, Any]] = []
        self.installed_keys: set[tuple[str, str]] = set()
        self.pending_actions: dict[tuple[str, str], str] = {}
        self.pending_update_packages: dict[tuple[str, str], str] = {}
        self.pending_update_sources: set[str] = set()
        self.refreshing_metadata_sources: set[str] = set()
        self.pending_manager_installs: set[str] = set()
        self.update_queue: list[dict[str, Any]] = []
        self.update_source_queue: list[str] = []
        self.batch_update_sources: set[str] = set()
        self.batch_update_errors: list[str] = []
        self.log_lines: list[str] = []
        self.search_token = 0
        self.suspend_events = False

        self.build_ui()
        self.refresh_status()
        self.show_empty(self.results_list, tr("empty_discover"))
        self.show_empty(self.installed_list, tr("loading_installed"))
        self.load_installed()
        self.refresh_package_databases()
        if not skip_admin:
            self.prepare_admin()

    def build_ui(self) -> None:
        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        root.add_css_class("root")
        self.set_child(root)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        main.add_css_class("main")
        main.set_hexpand(True)
        root.append(main)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.set_valign(Gtk.Align.CENTER)
        main.append(header)

        brand_mark = Gtk.Image.new_from_file(str(ICON_SOURCE)) if ICON_SOURCE.exists() else Gtk.Image.new_from_icon_name("package-x-generic")
        brand_mark.set_pixel_size(54)
        brand_mark.add_css_class("brand-mark")
        header.append(brand_mark)

        brand = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        header.append(brand)
        title = Gtk.Label(label=tr("title"))
        title.set_xalign(0)
        title.add_css_class("brand-title")
        brand.append(title)
        subtitle = Gtk.Label(label=tr("tagline"))
        subtitle.set_xalign(0)
        subtitle.add_css_class("brand-subtitle")
        brand.append(subtitle)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(tr("search_placeholder"))
        self.search_entry.add_css_class("search-entry")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("activate", lambda _entry: self.search_all_sources())
        self.search_entry.connect("search-changed", self.on_search_changed)
        header.append(self.search_entry)

        search_button = Gtk.Button(label=tr("search"))
        search_button.add_css_class("primary")
        search_button.connect("clicked", lambda _button: self.search_all_sources())
        header.append(search_button)

        gui_filter = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        gui_filter.set_valign(Gtk.Align.CENTER)
        header.append(gui_filter)
        gui_filter.append(Gtk.Label(label=tr("apps_only")))
        self.only_gui_switch = Gtk.Switch()
        self.only_gui_switch.set_active(True)
        self.only_gui_switch.connect("notify::active", self.on_gui_filter_changed)
        gui_filter.append(self.only_gui_switch)

        language_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        language_box.set_valign(Gtk.Align.CENTER)
        header.append(language_box)
        language_box.append(Gtk.Label(label=tr("language")))
        self.language_combo = Gtk.ComboBoxText()
        self.language_combo.append("de", "Deutsch")
        self.language_combo.append("en", "English")
        self.language_combo.set_active_id(LANGUAGE)
        self.language_combo.connect("changed", self.on_language_changed)
        language_box.append(self.language_combo)

        frontend_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        frontend_box.set_valign(Gtk.Align.CENTER)
        header.append(frontend_box)
        frontend_box.append(Gtk.Label(label=tr("frontend")))
        self.frontend_combo = Gtk.ComboBoxText()
        self.frontend_combo.append("auto", tr("frontend_auto"))
        self.frontend_combo.append("qt", tr("frontend_qt"))
        self.frontend_combo.append("gtk", tr("frontend_gtk"))
        self.frontend_combo.set_active_id(core.frontend_preference())
        self.frontend_combo.connect("changed", self.on_frontend_changed)
        frontend_box.append(self.frontend_combo)

        tabs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        tabs.add_css_class("tabs")
        main.append(tabs)
        self.tab_buttons: dict[str, Gtk.Button] = {}
        for view, label in (("discover", tr("discover")), ("installed", tr("installed")), ("updates", tr("updates")), ("manual", tr("manual"))):
            button = Gtk.Button(label=label)
            button.add_css_class("tab-button")
            button.connect("clicked", lambda _button, selected=view: self.set_view(selected))
            tabs.append(button)
            self.tab_buttons[view] = button

        self.source_chips = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        main.append(self.source_chips)

        self.stack = Gtk.Stack()
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        main.append(self.stack)

        self.results_title = Gtk.Label(label=tr("discover"))
        self.results_title.add_css_class("section-title")
        self.results_title.set_xalign(0)
        self.results_list = Gtk.ListBox()
        self.results_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.stack.add_named(self.make_list_page(self.results_title, self.results_list), "discover")

        self.installed_title = Gtk.Label(label=tr("installed"))
        self.installed_title.add_css_class("section-title")
        self.installed_title.set_xalign(0)
        self.installed_list = Gtk.ListBox()
        self.installed_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.stack.add_named(self.make_installed_page(), "installed")

        self.updates_list = Gtk.ListBox()
        self.updates_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.stack.add_named(self.make_updates_page(), "updates")

        self.stack.add_named(self.make_manual_page(), "manual")
        self.set_view("discover")

    def on_language_changed(self, combo: Gtk.ComboBoxText) -> None:
        language = combo.get_active_id()
        if not language or language == LANGUAGE:
            return
        query = self.search_entry.get_text()
        only_gui = self.only_gui_switch.get_active()
        view = self.current_view
        set_language(language)
        self.suspend_events = True
        self.set_child(None)
        self.build_ui()
        self.search_entry.set_text(query)
        self.only_gui_switch.set_active(only_gui)
        self.render_source_chips()
        self.render_updates()
        if self.results:
            if query.strip():
                self.results_title.set_text(tr("search_results", query=query.strip()))
            self.render_results()
        else:
            self.show_empty(self.results_list, tr("empty_discover"))
        self.render_installed()
        self.set_view(view)
        self.suspend_events = False

    def on_frontend_changed(self, combo: Gtk.ComboBoxText) -> None:
        if self.suspend_events:
            return
        preference = combo.get_active_id() or "auto"
        if preference == core.frontend_preference():
            return
        core.set_frontend_preference(preference)
        self.log(tr("frontend_restart"))

    def make_list_page(self, title: Gtk.Label, list_box: Gtk.ListBox) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.append(title)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(list_box)
        page.append(scroll)
        return page

    def make_installed_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        page.append(top)
        top.append(self.installed_title)
        self.installed_meta = Gtk.Label(label="")
        self.installed_meta.add_css_class("muted")
        top.append(self.installed_meta)
        refresh = Gtk.Button(label=tr("refresh"))
        refresh.add_css_class("secondary")
        refresh.connect("clicked", lambda _button: self.load_installed())
        top.append(refresh)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(self.installed_list)
        page.append(scroll)
        return page

    def make_updates_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        update_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        page.append(update_header)
        title = Gtk.Label(label=tr("updates"))
        title.set_xalign(0)
        title.add_css_class("section-title")
        update_header.append(title)
        self.updates_meta = Gtk.Label(label="")
        self.updates_meta.add_css_class("muted")
        update_header.append(self.updates_meta)
        refresh = Gtk.Button(label=tr("refresh"))
        refresh.add_css_class("secondary")
        refresh.connect("clicked", lambda _button: self.load_updates())
        update_header.append(refresh)
        all_button = Gtk.Button(label=tr("update_all"))
        all_button.add_css_class("primary")
        all_button.connect("clicked", lambda _button: self.update_all_sources())
        update_header.append(all_button)

        self.show_empty(self.updates_list, tr("checking_updates"))
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(self.updates_list)
        page.append(scroll)
        return page

    def make_manual_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        title = Gtk.Label(label=tr("manual_install"))
        title.set_xalign(0)
        title.add_css_class("section-title")
        page.append(title)

        grid = Gtk.Grid(column_spacing=16, row_spacing=16)
        grid.set_column_homogeneous(True)
        page.append(grid)

        appimage = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        appimage.add_css_class("tool-panel")
        grid.attach(appimage, 0, 0, 1, 1)
        appimage.append(Gtk.Label(label="AppImage", xalign=0, css_classes=["package-name"]))
        self.appimage_name = TextField("Name", "Obsidian")
        self.appimage_path = PathField(tr("appimage_file"), "/home/user/Downloads/App.AppImage", self)
        self.appimage_icon = PathField(tr("desktop_launcher_logo"), "/home/user/Pictures/logo.png", self)
        appimage.append(self.appimage_name)
        appimage.append(self.appimage_path)
        appimage.append(self.appimage_icon)
        appimage_button = Gtk.Button(label=tr("install_appimage"))
        appimage_button.add_css_class("primary")
        appimage_button.connect("clicked", lambda _button: self.install_appimage())
        appimage.append(appimage_button)

        archive = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        archive.add_css_class("tool-panel")
        grid.attach(archive, 1, 0, 1, 1)
        archive.append(Gtk.Label(label=tr("archive"), xalign=0, css_classes=["package-name"]))
        self.archive_name = TextField("Name", "Toolbox")
        self.archive_path = PathField(tr("archive_file"), "/home/user/Downloads/tool.tar.gz", self)
        self.archive_executable = TextField(tr("executable_inside_archive"), "bin/tool")
        self.archive_icon = PathField(tr("desktop_launcher_logo"), "/home/user/Pictures/icon.svg", self)
        archive.append(self.archive_name)
        archive.append(self.archive_path)
        archive.append(self.archive_executable)
        archive.append(self.archive_icon)
        archive_button = Gtk.Button(label=tr("install_archive"))
        archive_button.add_css_class("primary")
        archive_button.connect("clicked", lambda _button: self.install_archive())
        archive.append(archive_button)

        source_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        source_panel.add_css_class("tool-panel")
        grid.attach(source_panel, 0, 1, 2, 1)
        source_panel.append(Gtk.Label(label=tr("native_source"), xalign=0, css_classes=["panel-title"]))
        source_grid = Gtk.Grid(column_spacing=12, row_spacing=12)
        source_grid.set_column_homogeneous(True)
        source_panel.append(source_grid)

        manager_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        manager_box.append(Gtk.Label(label=tr("manager"), xalign=0, css_classes=["field-label"]))
        self.source_manager_combo = Gtk.ComboBoxText()
        for source_id, label in SOURCES:
            if source_id in core.SYSTEM_SOURCE_ORDER:
                self.source_manager_combo.append(source_id, label)
        self.source_manager_combo.set_active_id(core.native_package_source() or "apt")
        manager_box.append(self.source_manager_combo)
        source_grid.attach(manager_box, 0, 0, 1, 1)

        self.source_name = TextField(tr("source_name"), "vendor-tools")
        self.source_url = TextField(tr("source_url"), "https://repo.example.com/packages")
        self.source_key_url = TextField(tr("key_url"), "https://repo.example.com/signing-key.gpg")
        self.source_distribution = TextField(tr("distribution"), core.os_release_codename() or "stable")
        self.source_components = TextField(tr("components"), "main")
        source_grid.attach(self.source_name, 1, 0, 1, 1)
        source_grid.attach(self.source_url, 0, 1, 2, 1)
        source_grid.attach(self.source_key_url, 0, 2, 2, 1)
        source_grid.attach(self.source_distribution, 0, 3, 1, 1)
        source_grid.attach(self.source_components, 1, 3, 1, 1)
        add_button = Gtk.Button(label=tr("add_source"))
        add_button.add_css_class("primary")
        add_button.connect("clicked", lambda _button: self.add_package_source())
        source_panel.append(add_button)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(page)
        return scroll

    def set_view(self, view: str) -> None:
        self.current_view = view
        self.stack.set_visible_child_name(view)
        for name, button in self.tab_buttons.items():
            if name == view:
                button.add_css_class("active")
            else:
                button.remove_css_class("active")
        if view == "installed":
            self.render_installed()
        if view == "updates":
            if self.only_gui_switch.get_active():
                self.only_gui_switch.set_active(False)
            else:
                self.render_updates()
            if not self.updates:
                self.load_updates()

    def on_search_changed(self, _entry: Gtk.SearchEntry) -> None:
        if self.suspend_events:
            return
        if self.current_view == "installed":
            self.render_installed()
        if self.current_view == "updates":
            self.render_updates()

    def on_gui_filter_changed(self, _switch: Gtk.Switch, _param: Any) -> None:
        if self.suspend_events:
            return
        self.render_installed()
        if self.current_view == "updates":
            self.render_updates()
        if self.current_view == "discover" and len(self.search_entry.get_text().strip()) >= 2:
            self.search_all_sources()

    def refresh_status(self) -> None:
        def done(data: Any, error: Exception | None) -> bool:
            if error:
                self.log(tr("source_status_failed", error=error))
                return False
            self.status_data = data
            self.render_source_chips()
            return False

        run_in_thread(core.status, done)

    def refresh_package_databases(self) -> None:
        source = core.native_package_source()
        try:
            self.refreshing_metadata_sources.add(source)
            self.pending_update_sources.add(source)
            self.render_updates()
            label, command = core.refresh_metadata_command(source)
            job = core.start_job(label, command)
            self.watch_job(job.id, update_source=source, refresh_status_after=True, show_failure_dialog=False)
        except Exception as exc:  # noqa: BLE001 - best-effort background task
            self.pending_update_sources.discard(source)
            self.refreshing_metadata_sources.discard(source)
            self.render_updates()
            self.log(str(exc))

    def render_source_chips(self) -> None:
        while child := self.source_chips.get_first_child():
            self.source_chips.remove(child)
        sources = self.status_data.get("sources", {}) if self.status_data else {}
        installable_managers = {str(tool.get("id")): str(tool.get("name")) for tool in core.package_manager_tools()}
        for source_id, label in SOURCES:
            meta = sources.get(source_id, {})
            chip_text = f"{label}: {tr('ready') if meta.get('available') else tr('missing')}"
            if source_id in self.pending_manager_installs and source_id in installable_managers:
                chip = Gtk.Label(label=tr("installing_manager_chip", name=installable_managers[source_id]))
            elif not meta.get("available") and source_id in installable_managers:
                manager_name = installable_managers[source_id]
                chip = Gtk.Button(label=tr("install_missing_manager_chip", name=manager_name))
                chip.set_tooltip_text(tr("install_missing_manager_prompt", name=manager_name))
                chip.connect("clicked", lambda _button, selected=source_id, manager_name=installable_managers[source_id]: self.offer_install_manager_tool(selected, manager_name))
            else:
                chip = Gtk.Label(label=chip_text)
            chip.add_css_class("chip")
            if not meta.get("available"):
                chip.add_css_class("off")
            self.source_chips.append(chip)

    @staticmethod
    def source_label(source_id: str) -> str:
        return next((label for item_id, label in SOURCES if item_id == source_id), source_id)

    def log(self, message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self.log_lines.append(f"[{stamp}] {message}")
        self.log_lines = self.log_lines[-180:]

    @staticmethod
    def package_key(item: dict[str, Any]) -> tuple[str, str]:
        source = str(item.get("source", ""))
        package = str(item.get("packageName") or item.get("id") or item.get("name") or "").casefold()
        return source, package

    def is_installed(self, item: dict[str, Any]) -> bool:
        source, package = self.package_key(item)
        return bool(package) and (source, package) in self.installed_keys

    def clear_list(self, list_box: Gtk.ListBox) -> None:
        while child := list_box.get_first_child():
            list_box.remove(child)

    def show_empty(self, list_box: Gtk.ListBox, text: str) -> None:
        self.clear_list(list_box)
        label = Gtk.Label(label=text)
        label.add_css_class("empty")
        row = Gtk.ListBoxRow()
        row.set_selectable(False)
        row.set_child(label)
        list_box.append(row)

    def search_all_sources(self) -> None:
        query = self.search_entry.get_text().strip()
        self.set_view("discover")
        if len(query) < 2:
            self.show_empty(self.results_list, tr("min_chars"))
            return
        self.search_token += 1
        token = self.search_token
        self.results = []
        include_non_gui = not self.only_gui_switch.get_active()
        mode = tr("mode_all") if include_non_gui else tr("mode_gui")
        self.show_empty(self.results_list, tr("searching", mode=mode))
        self.results_title.set_text(tr("search_results", query=query))
        self.log(tr("search_started", query=query, mode=mode))

        def done(items: Any, error: Exception | None) -> bool:
            if token != self.search_token:
                return False
            if error:
                self.show_empty(self.results_list, tr("search_failed", error=error))
                self.log(tr("search_failed", error=error))
                return False
            self.results = items
            if not self.results:
                self.show_empty(self.results_list, tr("no_results"))
            else:
                self.render_results()
            self.log(tr("search_finished", count=len(self.results)))
            return False

        run_in_thread(lambda: core.search_all_packages(query, include_non_gui=include_non_gui), done)

    def render_results(self) -> None:
        self.clear_list(self.results_list)
        for item in self.results:
            if self.is_installed(item):
                row = PackageRow(item, tr("remove"), "danger", self.uninstall_package)
            else:
                row = PackageRow(item, tr("install"), "primary", self.install_package)
            pending = self.pending_actions.get(self.package_key(item))
            if pending == "install":
                row.set_busy(tr("installing_now"))
            elif pending == "remove":
                row.set_busy(tr("removing_now"))
            self.results_list.append(row)

    def load_updates(self) -> None:
        if hasattr(self, "updates_list"):
            self.show_empty(self.updates_list, tr("checking_updates"))

        def done(items: Any, error: Exception | None) -> bool:
            if error:
                self.log(tr("updates_check_failed", error=error))
                self.show_empty(self.updates_list, tr("updates_check_failed", error=error))
                return False
            self.updates = items
            self.render_updates()
            return False

        run_in_thread(lambda: core.list_all_updates(include_non_gui=True), done)

    def visible_updates(self) -> list[dict[str, Any]]:
        query = self.search_entry.get_text().strip().lower() if self.current_view == "updates" else ""
        items = self.updates
        if self.only_gui_switch.get_active():
            items = [item for item in items if item.get("gui")]
        if query:
            items = [
                item
                for item in items
                if query in str(item.get("name", "")).lower()
                or query in str(item.get("source", "")).lower()
                or query in str(item.get("packageName", "")).lower()
            ]
        active_batch_sources = (self.batch_update_sources & self.pending_update_sources) - self.refreshing_metadata_sources
        if active_batch_sources:
            items = sorted(
                items,
                key=lambda item: (
                    0 if str(item.get("source", "")) in active_batch_sources else 1,
                    str(item.get("source", "")),
                    str(item.get("name", "")).lower(),
                ),
            )
        return items

    def render_updates(self) -> None:
        if not hasattr(self, "updates_list"):
            return
        items = self.visible_updates()
        self.updates_meta.set_text(tr("updates_found", count=len(items)) if items else "")
        if not items:
            query = self.search_entry.get_text().strip()
            filtered = bool(self.updates and (query or self.only_gui_switch.get_active()))
            message = tr("updating_now") if self.pending_update_sources or self.update_source_queue else tr("no_updates_filtered" if filtered else "no_updates")
            self.show_empty(self.updates_list, message)
            return
        self.clear_list(self.updates_list)
        for item in items:
            row = PackageRow(item, tr("update"), "primary", self.update_package)
            pending = self.pending_update_packages.get(self.package_key(item))
            if pending or item.get("source") in self.pending_update_sources or item.get("source") in self.update_source_queue:
                row.set_busy(tr("updating_now"))
            self.updates_list.append(row)

    def load_installed(self) -> None:
        def done(items: Any, error: Exception | None) -> bool:
            if error:
                self.log(tr("installed_load_failed_log", error=error))
                self.show_empty(self.installed_list, tr("installed_load_failed"))
                return False
            self.installed = items
            self.installed_keys = {
                key for key in (self.package_key(item) for item in self.installed) if key[1]
            }
            self.render_installed()
            if self.results:
                self.render_results()
            return False

        run_in_thread(lambda: core.list_installed("all"), done)

    def render_installed(self) -> None:
        query = self.search_entry.get_text().strip().lower() if self.current_view == "installed" else ""
        visible_installed = [item for item in self.installed if item.get("source") != "desktop"]
        items = visible_installed
        if self.only_gui_switch.get_active():
            items = [item for item in items if item.get("gui")]
        if query:
            items = [
                item
                for item in items
                if query in str(item.get("name", "")).lower()
                or query in str(item.get("source", "")).lower()
                or query in str(item.get("path", "")).lower()
                or query in str(item.get("packageName", "")).lower()
            ]
        self.installed_meta.set_text(tr("entries_count", count=len(items), total=len(visible_installed)))
        if not items:
            self.show_empty(self.installed_list, tr("no_installed"))
            return
        self.clear_list(self.installed_list)
        for item in sorted(items, key=lambda value: (value.get("source", ""), value.get("name", "").lower())):
            self.installed_list.append(PackageRow(item, tr("remove"), "danger", self.uninstall_package))

    def update_package(self, item: dict[str, Any], row: PackageRow | None = None, continue_queue: bool = False) -> None:
        package_key = self.package_key(item)
        self.pending_update_packages[package_key] = "update"
        if row:
            row.set_busy(tr("updating_now"))
        source = str(item.get("source", ""))
        name = str(item.get("packageName") or item.get("id") or item.get("name") or "")
        try:
            label, command = core.update_command(source, name)
            job = core.start_job(label, command)
            self.log(tr("update_started", source=self.source_label(source)))
            self.watch_job(job.id, update_package=package_key, continue_update_queue=continue_queue)
        except Exception as exc:  # noqa: BLE001 - UI boundary
            self.pending_update_packages.pop(package_key, None)
            if row:
                row.clear_busy()
            self.log(tr("update_failed", error=exc))
            self.show_error_details(tr("update_failed", error=exc), str(exc))
            if continue_queue:
                self.start_next_queued_update()

    def update_all_sources(self) -> None:
        sources = self.status_data.get("sources", {}) if self.status_data else {}
        queued: list[str] = []
        queued_sources = set(self.update_source_queue)
        for source, _label in SOURCES:
            if source in {"manual", "desktop"}:
                continue
            already_running = source in self.pending_update_sources and source not in self.refreshing_metadata_sources
            if sources.get(source, {}).get("available") and source not in queued_sources and not already_running:
                queued.append(source)
                queued_sources.add(source)
        self.batch_update_errors = []
        self.batch_update_sources = set(queued)
        self.update_source_queue.extend(queued)
        self.render_updates()
        self.start_next_queued_update_source()

    def start_next_queued_update(self) -> None:
        if self.pending_update_packages:
            return
        while self.update_queue:
            item = self.update_queue.pop(0)
            if self.package_key(item) not in self.pending_update_packages:
                self.update_package(item, continue_queue=True)
                return

    def start_next_queued_update_source(self) -> None:
        if self.pending_update_sources:
            return
        while self.update_source_queue:
            source = self.update_source_queue.pop(0)
            if source not in self.pending_update_sources:
                self.update_source(source, continue_queue=True)
                return

    def update_source(self, source: str, continue_queue: bool = False) -> None:
        self.pending_update_sources.add(source)
        self.render_updates()
        try:
            label, command = core.update_command(source)
            job = core.start_job(label, command)
            self.log(tr("update_started", source=self.source_label(source)))
            self.watch_job(job.id, update_source=source, continue_update_queue=continue_queue, show_failure_dialog=not continue_queue)
        except Exception as exc:  # noqa: BLE001 - UI boundary
            self.pending_update_sources.discard(source)
            self.batch_update_sources.discard(source)
            self.render_updates()
            self.log(tr("update_failed", error=exc))
            self.show_error_details(tr("update_failed", error=exc), str(exc))
            if continue_queue:
                self.start_next_queued_update_source()

    def add_package_source(self) -> None:
        manager = self.source_manager_combo.get_active_id() if hasattr(self, "source_manager_combo") else core.native_package_source()
        payload = {
            "manager": manager,
            "name": self.source_name.get_text(),
            "url": self.source_url.get_text(),
            "keyUrl": self.source_key_url.get_text(),
            "distribution": self.source_distribution.get_text(),
            "components": self.source_components.get_text(),
        }
        try:
            label, command = core.add_package_source_command(payload)
            job = core.start_job(label, command)
            self.log(tr("add_source_started", name=payload["name"]))
            self.watch_job(job.id, refresh_status_after=True)
        except Exception as exc:  # noqa: BLE001 - UI boundary
            self.log(tr("add_source_failed", error=exc))
            self.show_error_details(tr("add_source_failed", error=exc), str(exc))

    def offer_install_manager_tool(self, tool_id: str, name: str) -> None:
        dialog = Gtk.Window(title=tr("install_manager"), transient_for=self, modal=True)
        dialog.set_default_size(420, 160)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        root.set_margin_top(18)
        root.set_margin_bottom(18)
        root.set_margin_start(18)
        root.set_margin_end(18)
        dialog.set_child(root)

        prompt = Gtk.Label(label=tr("install_missing_manager_prompt", name=name))
        prompt.set_xalign(0)
        prompt.set_wrap(True)
        prompt.add_css_class("panel-title")
        root.append(prompt)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        actions.set_halign(Gtk.Align.END)
        root.append(actions)
        no_button = Gtk.Button(label=tr("no"))
        no_button.add_css_class("secondary")
        no_button.connect("clicked", lambda _button: dialog.close())
        actions.append(no_button)
        yes_button = Gtk.Button(label=tr("yes"))
        yes_button.add_css_class("primary")

        def install(_button: Gtk.Button) -> None:
            dialog.close()
            self.install_manager_tool(tool_id, name)

        yes_button.connect("clicked", install)
        actions.append(yes_button)
        dialog.present()

    def install_manager_tool(self, tool_id: str, name: str, row: ActionRow | None = None) -> None:
        self.pending_manager_installs.add(tool_id)
        self.render_source_chips()
        if row:
            row.set_busy(tr("installing_now"))
        try:
            label, command = core.install_package_manager_command(tool_id)
            job = core.start_job(label, command)
            self.log(tr("install_manager_started", name=name))
            self.watch_job(job.id, manager_tool=tool_id)
        except Exception as exc:  # noqa: BLE001 - UI boundary
            self.pending_manager_installs.discard(tool_id)
            self.render_source_chips()
            if row:
                row.clear_busy()
            self.log(tr("install_manager_failed", error=exc))
            self.show_error_details(tr("install_manager_failed", error=exc), str(exc))

    def install_package(self, item: dict[str, Any], row: PackageRow) -> None:
        package_key = self.package_key(item)
        self.pending_actions[package_key] = "install"
        row.set_busy(tr("installing_now"))
        source = item.get("source", "")
        name = item.get("packageName") or item.get("id") or item.get("name", "")
        try:
            label, command = core.install_command(source, name)
            job = core.start_job(label, command)
            self.watch_job(job.id, package_key)
        except Exception as exc:  # noqa: BLE001 - UI boundary
            self.pending_actions.pop(package_key, None)
            row.clear_busy()
            self.log(str(exc))
            self.show_error_details(str(exc), str(exc))

    def uninstall_package(self, item: dict[str, Any], row: PackageRow) -> None:
        package_key = self.package_key(item)
        self.pending_actions[package_key] = "remove"
        row.set_busy(tr("removing_now"))
        source = item.get("source", "")
        name = item.get("packageName") or item.get("id") or item.get("name", "")
        if source == "manual":
            def done(_entry: Any, error: Exception | None) -> bool:
                self.pending_actions.pop(package_key, None)
                if error:
                    self.log(tr("removal_failed", error=error))
                    self.show_error_details(tr("removal_failed", error=error), str(error))
                else:
                    self.log(tr("removed", name=name))
                    self.load_installed()
                if self.results:
                    self.render_results()
                return False

            run_in_thread(lambda: core.uninstall_manual(str(name)), done)
            return
        try:
            label, command = core.uninstall_command(source, name)
            job = core.start_job(label, command)
            self.watch_job(job.id, package_key)
        except Exception as exc:  # noqa: BLE001 - UI boundary
            self.pending_actions.pop(package_key, None)
            row.clear_busy()
            self.log(str(exc))
            self.show_error_details(str(exc), str(exc))

    def watch_job(
        self,
        job_id: str,
        package_key: tuple[str, str] | None = None,
        update_package: tuple[str, str] | None = None,
        update_source: str | None = None,
        manager_tool: str | None = None,
        refresh_status_after: bool = False,
        continue_update_queue: bool = False,
        show_failure_dialog: bool = True,
    ) -> None:
        self.log(tr("job_started", job_id=job_id))
        last_len = 0

        def poll() -> bool:
            nonlocal last_len
            job = core.JOBS.get(job_id)
            if not job:
                self.log(tr("job_not_found"))
                return False
            for line in job.output[last_len:]:
                self.log(line)
            last_len = len(job.output)
            if job.state in {"done", "failed"}:
                self.log(f"{job.label}: {job.state} ({job.exit_code})")
                if package_key:
                    self.pending_actions.pop(package_key, None)
                if update_package:
                    self.pending_update_packages.pop(update_package, None)
                    self.render_updates()
                if update_source:
                    metadata_refresh = update_source in self.refreshing_metadata_sources
                    self.pending_update_sources.discard(update_source)
                    self.refreshing_metadata_sources.discard(update_source)
                    if not metadata_refresh:
                        self.batch_update_sources.discard(update_source)
                    self.render_updates()
                if manager_tool:
                    self.pending_manager_installs.discard(manager_tool)
                    self.render_source_chips()
                    self.refresh_status()
                if refresh_status_after:
                    self.refresh_status()
                details = "\n".join(job.output[-120:]) or tr("no_job_output")
                if job.state == "failed" and update_source and continue_update_queue:
                    self.batch_update_errors.append(f"{job.label} ({job.exit_code})\n{details}")
                if job.state == "failed" and show_failure_dialog:
                    message = tr("job_failed", label=job.label, code=job.exit_code)
                    self.log(message)
                    self.show_error_details(message, details)
                if job.state == "done" and manager_tool:
                    tool = next((item for item in core.package_manager_tools() if str(item.get("id")) == manager_tool), None)
                    if tool and not tool.get("installed"):
                        name = str(tool.get("name") or manager_tool)
                        message = tr("install_manager_missing_after", name=name)
                        self.log(message)
                        self.show_error_details(message, details)
                if self.results:
                    self.render_results()
                self.load_installed()
                if update_package:
                    self.load_updates()
                if continue_update_queue or self.update_queue:
                    self.start_next_queued_update()
                if update_source:
                    if self.update_source_queue:
                        self.start_next_queued_update_source()
                    else:
                        self.load_updates()
                        if self.batch_update_errors:
                            details = "\n\n".join(self.batch_update_errors)
                            self.batch_update_errors = []
                            self.show_error_details(tr("update_failed", error="one or more package managers failed"), details)
                return False
            return True

        GLib.timeout_add(700, poll)

    def install_appimage(self) -> None:
        payload = {
            "name": self.appimage_name.get_text(),
            "appimagePath": self.appimage_path.get_text(),
            "iconPath": self.appimage_icon.get_text(),
        }

        def done(entry: Any, error: Exception | None) -> bool:
            if error:
                self.log(tr("appimage_failed", error=error))
                self.show_error_details(tr("appimage_failed", error=error), str(error))
            else:
                self.log(tr("appimage_installed", name=entry.get("name")))
                self.load_installed()
            return False

        run_in_thread(lambda: core.install_appimage(payload), done)

    def install_archive(self) -> None:
        payload = {
            "name": self.archive_name.get_text(),
            "archivePath": self.archive_path.get_text(),
            "executable": self.archive_executable.get_text(),
            "iconPath": self.archive_icon.get_text(),
        }

        def done(entry: Any, error: Exception | None) -> bool:
            if error:
                self.log(tr("archive_failed", error=error))
                self.show_error_details(tr("archive_failed", error=error), str(error))
            else:
                self.log(tr("archive_installed", name=entry.get("name")))
                self.load_installed()
            return False

        run_in_thread(lambda: core.install_archive(payload), done)

    def show_error_details(self, title: str, details: str) -> None:
        dialog = Gtk.Window(title=tr("error_details"), transient_for=self, modal=True)
        dialog.set_default_size(720, 420)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(16)
        root.set_margin_bottom(16)
        root.set_margin_start(16)
        root.set_margin_end(16)
        dialog.set_child(root)

        title_label = Gtk.Label(label=title)
        title_label.set_xalign(0)
        title_label.set_wrap(True)
        title_label.add_css_class("panel-title")
        root.append(title_label)

        text = Gtk.TextView()
        text.set_editable(False)
        text.set_monospace(True)
        text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text.get_buffer().set_text(details)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(text)
        root.append(scroll)

        close = Gtk.Button(label=tr("close"))
        close.add_css_class("secondary")
        close.set_halign(Gtk.Align.END)
        close.connect("clicked", lambda _button: dialog.close())
        root.append(close)
        dialog.present()

    def prepare_admin(self) -> None:
        def admin() -> str:
            if os.geteuid() == 0:
                return tr("admin_already_root")
            if core.which("pkexec"):
                proc = subprocess.run(
                    ["pkexec", "true"],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=False,
                    timeout=180,
                )
                if proc.returncode == 0:
                    return tr("admin_authorized")
                return tr("admin_not_confirmed")
            if core.sudo_askpass_ready():
                proc = subprocess.run(
                    ["sudo", "-A", "-v"],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=False,
                    timeout=180,
                )
                if proc.returncode == 0:
                    return tr("admin_sudo_authorized")
                return tr("admin_sudo_not_confirmed")
            if core.which("sudo"):
                return tr("sudo_askpass_unsupported")
            return tr("unknown_admin")

        def done(message: Any, error: Exception | None) -> bool:
            self.log(str(error or message))
            return False

        self.log(tr("admin_prepare"))
        run_in_thread(admin, done)


class SoftwareManagerApp(Gtk.Application):
    def __init__(self, skip_admin: bool = False):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.skip_admin = skip_admin
        self.window: MainWindow | None = None

    def do_activate(self) -> None:
        display = Gdk.Display.get_default()
        if display:
            provider = Gtk.CssProvider()
            provider.load_from_data(CSS.encode("utf-8"))
            Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        if self.window is None:
            self.window = MainWindow(self, skip_admin=self.skip_admin)
            self.window.connect("close-request", self.on_window_close)
        self.window.present()

    def on_window_close(self, _window: Gtk.Window) -> bool:
        self.window = None
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument("--install-launcher", action="store_true", help="Install the desktop launcher")
    parser.add_argument("--check", action="store_true", help="Check dependencies")
    parser.add_argument("--lang", choices=("de", "en"), help="Override UI language")
    parser.add_argument("--skip-admin", action="store_true", help="Skip admin warmup")
    parser.add_argument("--background-refresh", action="store_true", help="Refresh package databases without opening the UI")
    args = parser.parse_args()
    if args.lang:
        set_language(args.lang)

    if args.install_launcher:
        install_launcher()
        print(f"Launcher installed: {DESKTOP_FILE}")
        return 0
    if args.check:
        print("GTK4 ok")
        print("Core ok")
        print("Sources:", ", ".join(label for _source, label in SOURCES))
        return 0
    if args.background_refresh:
        code, output = core.refresh_system_databases()
        if output:
            print(output)
        return code

    if ASKPASS_SCRIPT.exists():
        os.environ.setdefault("SUDO_ASKPASS", str(ASKPASS_SCRIPT))

    app = SoftwareManagerApp(skip_admin=args.skip_admin)
    return app.run([sys.argv[0]])


if __name__ == "__main__":
    raise SystemExit(main())
