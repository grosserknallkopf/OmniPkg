#!/usr/bin/env python3
"""Native Qt desktop shell for OmniPkg."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

import omnipkg_core as core


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
        "add_source": "Add source",
        "add_source_failed": "Adding source failed: {error}",
        "add_source_started": "Adding source: {name}",
        "admin_already_root": "The app is already running with root privileges.",
        "admin_authorized": "Admin authorization prepared.",
        "admin_not_confirmed": "Admin authorization was not confirmed. System packages will ask again later.",
        "admin_prepare": "Preparing admin authorization...",
        "admin_sudo_authorized": "Sudo authorization prepared.",
        "admin_sudo_not_confirmed": "Sudo authorization was not confirmed. System packages will ask again later.",
        "all_packages": "All packages",
        "appimage_file": "AppImage file",
        "appimage_failed": "AppImage failed: {error}",
        "appimage_installed": "{name} installed",
        "apps_only": "Apps only",
        "archive": "Archive",
        "archive_failed": "Archive failed: {error}",
        "archive_file": "Archive file",
        "archive_installed": "{name} installed",
        "checking_updates": "Checking for updates...",
        "choose_file": "Choose a file",
        "close": "Close",
        "components": "Components",
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
        "install_missing_manager_chip": "{name}: missing. install?",
        "install_missing_manager_prompt": "{name} is not installed. Install it now?",
        "installing_now": "Installing...",
        "installed": "Installed",
        "installed_load_failed": "Installed packages could not be loaded.",
        "installed_state": "Installed",
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
        "no": "No",
        "no_installed": "No installed entries found.",
        "no_job_output": "The package manager did not return any additional output.",
        "no_results": "No results in the available sources.",
        "no_updates": "No updates found.",
        "no_updates_filtered": "No updates match the current search or filter.",
        "pkexec_missing": "pkexec is missing. Install polkit/pkexec for graphical admin prompts.",
        "sudo_askpass_unsupported": "pkexec is missing and this sudo does not support askpass (-A). Install polkit/pkexec or a sudo build with askpass support.",
        "ready": "ready",
        "refresh": "Refresh",
        "remove": "Remove",
        "removal_failed": "Removal failed: {error}",
        "removed": "{name} removed",
        "removing_now": "Removing...",
        "search": "Search",
        "search_failed": "Search failed: {error}",
        "search_finished": "Search finished: {count} results",
        "search_placeholder": "Search apps, packages, AppImages, CLI tools or libraries",
        "search_results": "Search results for \"{query}\"",
        "search_started": "Search started: {query} ({mode})",
        "searching": "OmniPkg is searching {mode} across all available sources...",
        "source_name": "Source name",
        "source_status_failed": "Source status failed: {error}",
        "source_url": "Repository URL",
        "tagline": "One roof for all your package sources",
        "title": "OmniPkg",
        "unknown_admin": "Neither pkexec nor sudo was found. System-wide installs cannot start.",
        "update": "Update",
        "update_all": "Update all",
        "update_failed": "Update failed: {error}",
        "update_started": "Update started: {source}",
        "updates": "Updates",
        "updates_check_failed": "Updates could not be checked: {error}",
        "updates_found": "{count} updates available",
        "updating_now": "Updating...",
        "yes": "Yes",
    },
    "de": {
        "add_source": "Quelle hinzufügen",
        "add_source_failed": "Quelle konnte nicht hinzugefügt werden: {error}",
        "add_source_started": "Quelle wird hinzugefügt: {name}",
        "admin_already_root": "Die App läuft bereits mit Root-Rechten.",
        "admin_authorized": "Admin-Freigabe ist vorbereitet.",
        "admin_not_confirmed": "Admin-Freigabe wurde nicht bestätigt. Systempakete fragen später erneut nach.",
        "admin_prepare": "Admin-Freigabe wird vorbereitet...",
        "admin_sudo_authorized": "Sudo-Freigabe ist vorbereitet.",
        "admin_sudo_not_confirmed": "Sudo-Freigabe wurde nicht bestätigt. Systempakete fragen später erneut nach.",
        "all_packages": "Alle Pakete",
        "appimage_file": "AppImage-Datei",
        "appimage_failed": "AppImage fehlgeschlagen: {error}",
        "appimage_installed": "{name} installiert",
        "apps_only": "Nur Apps",
        "archive": "Archiv",
        "archive_failed": "Archiv fehlgeschlagen: {error}",
        "archive_file": "Archivdatei",
        "archive_installed": "{name} installiert",
        "checking_updates": "Updates werden gesucht...",
        "choose_file": "Datei auswählen",
        "close": "Schließen",
        "components": "Komponenten",
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
        "install_missing_manager_chip": "{name}: fehlt. installieren?",
        "install_missing_manager_prompt": "{name} ist nicht installiert. Jetzt installieren?",
        "installing_now": "Wird installiert...",
        "installed": "Installiert",
        "installed_load_failed": "Installierte Pakete konnten nicht geladen werden.",
        "installed_state": "Installiert",
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
        "no": "Nein",
        "no_installed": "Keine installierten Einträge gefunden.",
        "no_job_output": "Der Paketmanager hat keine weiteren Details ausgegeben.",
        "no_results": "Keine Treffer in den verfügbaren Quellen.",
        "no_updates": "Keine Updates gefunden.",
        "no_updates_filtered": "Keine Updates passen zur aktuellen Suche oder zum Filter.",
        "pkexec_missing": "pkexec fehlt. Installiere polkit/pkexec für grafische Admin-Abfragen.",
        "sudo_askpass_unsupported": "pkexec fehlt und dieses sudo unterstützt kein Askpass (-A). Installiere polkit/pkexec oder ein sudo mit Askpass-Unterstützung.",
        "ready": "bereit",
        "refresh": "Aktualisieren",
        "remove": "Deinstallieren",
        "removal_failed": "Entfernen fehlgeschlagen: {error}",
        "removed": "{name} entfernt",
        "removing_now": "Wird deinstalliert...",
        "search": "Suchen",
        "search_failed": "Suche fehlgeschlagen: {error}",
        "search_finished": "Suche abgeschlossen: {count} Treffer",
        "search_placeholder": "Apps, Pakete, AppImages, CLI-Tools oder Bibliotheken suchen",
        "search_results": "Suchergebnisse für \"{query}\"",
        "search_started": "Suche gestartet: {query} ({mode})",
        "searching": "OmniPkg sucht nach {mode} in allen verfügbaren Quellen...",
        "source_name": "Quellenname",
        "source_status_failed": "Quellenstatus fehlgeschlagen: {error}",
        "source_url": "Repository-URL",
        "tagline": "Ein Dach für alle Paketquellen",
        "title": "OmniPkg",
        "unknown_admin": "Weder pkexec noch sudo wurde gefunden. Systemweite Installationen können nicht starten.",
        "update": "Aktualisieren",
        "update_all": "Alle aktualisieren",
        "update_failed": "Aktualisierung fehlgeschlagen: {error}",
        "update_started": "Aktualisierung gestartet: {source}",
        "updates": "Updates",
        "updates_check_failed": "Updates konnten nicht geprüft werden: {error}",
        "updates_found": "{count} Updates verfügbar",
        "updating_now": "Wird aktualisiert...",
        "yes": "Ja",
    },
}

LANGUAGE = core.detected_language()


def set_language(language: str) -> None:
    global LANGUAGE
    LANGUAGE = "de" if language == "de" else "en"
    os.environ["OMNIPKG_LANG"] = LANGUAGE


def tr(key: str, **values: Any) -> str:
    text = TRANSLATIONS.get(LANGUAGE, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))
    return text.format(**values) if values else text


def load_qt() -> dict[str, Any]:
    errors: list[str] = []
    for binding in ("PyQt6", "PySide6", "PyQt5", "PySide2"):
        try:
            if binding == "PyQt6":
                from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal as Signal
                from PyQt6.QtGui import QIcon, QPixmap
                from PyQt6.QtWidgets import (
                    QApplication,
                    QCheckBox,
                    QComboBox,
                    QDialog,
                    QFileDialog,
                    QFormLayout,
                    QFrame,
                    QGridLayout,
                    QHBoxLayout,
                    QLabel,
                    QLineEdit,
                    QListWidget,
                    QListWidgetItem,
                    QMainWindow,
                    QMessageBox,
                    QPushButton,
                    QScrollArea,
                    QSizePolicy,
                    QTabWidget,
                    QTextEdit,
                    QVBoxLayout,
                    QWidget,
                )

                align_center = Qt.AlignmentFlag.AlignCenter
                align_right = Qt.AlignmentFlag.AlignRight
            elif binding == "PySide6":
                from PySide6.QtCore import QObject, Qt, QTimer, Signal
                from PySide6.QtGui import QIcon, QPixmap
                from PySide6.QtWidgets import (
                    QApplication,
                    QCheckBox,
                    QComboBox,
                    QDialog,
                    QFileDialog,
                    QFormLayout,
                    QFrame,
                    QGridLayout,
                    QHBoxLayout,
                    QLabel,
                    QLineEdit,
                    QListWidget,
                    QListWidgetItem,
                    QMainWindow,
                    QMessageBox,
                    QPushButton,
                    QScrollArea,
                    QSizePolicy,
                    QTabWidget,
                    QTextEdit,
                    QVBoxLayout,
                    QWidget,
                )

                align_center = Qt.AlignmentFlag.AlignCenter
                align_right = Qt.AlignmentFlag.AlignRight
            elif binding == "PyQt5":
                from PyQt5.QtCore import QObject, Qt, QTimer, pyqtSignal as Signal
                from PyQt5.QtGui import QIcon, QPixmap
                from PyQt5.QtWidgets import (
                    QApplication,
                    QCheckBox,
                    QComboBox,
                    QDialog,
                    QFileDialog,
                    QFormLayout,
                    QFrame,
                    QGridLayout,
                    QHBoxLayout,
                    QLabel,
                    QLineEdit,
                    QListWidget,
                    QListWidgetItem,
                    QMainWindow,
                    QMessageBox,
                    QPushButton,
                    QScrollArea,
                    QSizePolicy,
                    QTabWidget,
                    QTextEdit,
                    QVBoxLayout,
                    QWidget,
                )

                align_center = Qt.AlignCenter
                align_right = Qt.AlignRight
            else:
                from PySide2.QtCore import QObject, Qt, QTimer, Signal
                from PySide2.QtGui import QIcon, QPixmap
                from PySide2.QtWidgets import (
                    QApplication,
                    QCheckBox,
                    QComboBox,
                    QDialog,
                    QFileDialog,
                    QFormLayout,
                    QFrame,
                    QGridLayout,
                    QHBoxLayout,
                    QLabel,
                    QLineEdit,
                    QListWidget,
                    QListWidgetItem,
                    QMainWindow,
                    QMessageBox,
                    QPushButton,
                    QScrollArea,
                    QSizePolicy,
                    QTabWidget,
                    QTextEdit,
                    QVBoxLayout,
                    QWidget,
                )

                align_center = Qt.AlignCenter
                align_right = Qt.AlignRight
            return {
                "binding": binding,
                "QApplication": QApplication,
                "QCheckBox": QCheckBox,
                "QComboBox": QComboBox,
                "QDialog": QDialog,
                "QFileDialog": QFileDialog,
                "QFormLayout": QFormLayout,
                "QFrame": QFrame,
                "QGridLayout": QGridLayout,
                "QHBoxLayout": QHBoxLayout,
                "QIcon": QIcon,
                "QLabel": QLabel,
                "QLineEdit": QLineEdit,
                "QListWidget": QListWidget,
                "QListWidgetItem": QListWidgetItem,
                "QMainWindow": QMainWindow,
                "QMessageBox": QMessageBox,
                "QObject": QObject,
                "QPixmap": QPixmap,
                "QPushButton": QPushButton,
                "QScrollArea": QScrollArea,
                "QSizePolicy": QSizePolicy,
                "QTabWidget": QTabWidget,
                "QTextEdit": QTextEdit,
                "QTimer": QTimer,
                "QVBoxLayout": QVBoxLayout,
                "QWidget": QWidget,
                "Signal": Signal,
                "align_center": align_center,
                "align_right": align_right,
            }
        except ImportError as exc:
            errors.append(f"{binding}: {exc}")
    raise RuntimeError("No supported Qt Python binding found. Install PyQt6, PySide6, PyQt5 or PySide2.\n" + "\n".join(errors))


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


def run_qt_app(args: argparse.Namespace) -> int:
    qt = load_qt()
    QObject = qt["QObject"]
    Signal = qt["Signal"]
    QApplication = qt["QApplication"]
    QCheckBox = qt["QCheckBox"]
    QComboBox = qt["QComboBox"]
    QDialog = qt["QDialog"]
    QFileDialog = qt["QFileDialog"]
    QFormLayout = qt["QFormLayout"]
    QFrame = qt["QFrame"]
    QGridLayout = qt["QGridLayout"]
    QHBoxLayout = qt["QHBoxLayout"]
    QIcon = qt["QIcon"]
    QLabel = qt["QLabel"]
    QLineEdit = qt["QLineEdit"]
    QListWidget = qt["QListWidget"]
    QListWidgetItem = qt["QListWidgetItem"]
    QMainWindow = qt["QMainWindow"]
    QMessageBox = qt["QMessageBox"]
    QPixmap = qt["QPixmap"]
    QPushButton = qt["QPushButton"]
    QScrollArea = qt["QScrollArea"]
    QSizePolicy = qt["QSizePolicy"]
    QTabWidget = qt["QTabWidget"]
    QTextEdit = qt["QTextEdit"]
    QTimer = qt["QTimer"]
    QVBoxLayout = qt["QVBoxLayout"]
    QWidget = qt["QWidget"]
    align_center = qt["align_center"]
    align_right = qt["align_right"]

    class AsyncCall(QObject):
        finished = Signal(object, object)

        def __init__(self, fn: Callable[[], Any], callback: Callable[[Any, Exception | None], None]):
            super().__init__()
            self.fn = fn
            self.finished.connect(callback)

        def start(self) -> None:
            def worker() -> None:
                try:
                    self.finished.emit(self.fn(), None)
                except Exception as exc:  # noqa: BLE001 - UI boundary
                    self.finished.emit(None, exc)

            threading.Thread(target=worker, daemon=True).start()

    class PackageRow(QWidget):
        def __init__(self, item: dict[str, Any], action_label: str, role: str, callback: Callable[[dict[str, Any], "PackageRow"], None]):
            super().__init__()
            self.item = item
            layout = QHBoxLayout(self)
            layout.setContentsMargins(12, 11, 12, 11)
            layout.setSpacing(12)

            icon = QLabel()
            icon.setObjectName("packageIcon")
            icon.setFixedSize(48, 48)
            icon.setAlignment(align_center)
            self.set_icon(icon, item)
            layout.addWidget(icon)

            text_box = QVBoxLayout()
            text_box.setSpacing(3)
            layout.addLayout(text_box, 1)

            title = QLabel(item.get("name") or item.get("id") or "Untitled")
            title.setObjectName("packageName")
            title.setWordWrap(False)
            text_box.addWidget(title)

            description = QLabel(item.get("description") or item.get("path") or item.get("origin") or "")
            description.setObjectName("muted")
            description.setWordWrap(True)
            text_box.addWidget(description)

            package_name = item.get("packageName") if item.get("packageName") != item.get("name") else ""
            detail = " · ".join(str(value) for value in (item.get("source", "").upper(), package_name, item.get("repo"), item.get("version"), item.get("kind")) if value)
            meta = QLabel(detail)
            meta.setObjectName("meta")
            text_box.addWidget(meta)

            self.action_button = QPushButton(action_label)
            self.action_button.setProperty("role", role)
            self.action_button.clicked.connect(lambda: callback(item, self))
            layout.addWidget(self.action_button)

            self.busy_label = QLabel("")
            self.busy_label.setObjectName("muted")
            self.busy_label.hide()
            layout.addWidget(self.busy_label)

        def set_icon(self, label: Any, item: dict[str, Any]) -> None:
            icon = str(item.get("icon", "") or "").strip()
            if icon:
                icon_path = Path(icon).expanduser()
                if icon_path.exists():
                    pixmap = QPixmap(str(icon_path))
                    if not pixmap.isNull():
                        label.setPixmap(pixmap.scaled(34, 34))
                        return
            fallback = str(item.get("source") or item.get("name") or "?")[:1].upper()
            label.setText(fallback)

        def set_busy(self, text: str) -> None:
            self.action_button.setEnabled(False)
            self.action_button.hide()
            self.busy_label.setText(text)
            self.busy_label.show()

        def clear_busy(self) -> None:
            self.busy_label.hide()
            self.action_button.show()
            self.action_button.setEnabled(True)

    class PathField(QWidget):
        def __init__(self, placeholder: str):
            super().__init__()
            layout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            self.entry = QLineEdit()
            self.entry.setPlaceholderText(placeholder)
            layout.addWidget(self.entry, 1)
            choose = QPushButton("...")
            choose.clicked.connect(self.choose_file)
            layout.addWidget(choose)

        def choose_file(self) -> None:
            path, _selected = QFileDialog.getOpenFileName(self, tr("choose_file"))
            if path:
                self.entry.setText(path)

        def text(self) -> str:
            return self.entry.text().strip()

    class MainWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle(APP_TITLE)
            self.resize(1280, 780)
            if ICON_SOURCE.exists():
                self.setWindowIcon(QIcon(str(ICON_SOURCE)))
            self.status_data: dict[str, Any] | None = None
            self.results: list[dict[str, Any]] = []
            self.installed: list[dict[str, Any]] = []
            self.updates: list[dict[str, Any]] = []
            self.updates_loading = False
            self.installed_keys: set[tuple[str, str]] = set()
            self.pending_actions: dict[tuple[str, str], str] = {}
            self.pending_update_packages: dict[tuple[str, str], str] = {}
            self.pending_update_sources: set[str] = set()
            self.refreshing_metadata_sources: set[str] = set()
            self.pending_manager_installs: set[str] = set()
            self.update_source_queue: list[str] = []
            self.batch_update_sources: set[str] = set()
            self.batch_update_errors: list[str] = []
            self.log_lines: list[str] = []
            self.search_token = 0
            self._async_calls: list[AsyncCall] = []
            self._suspend_events = False
            self.build_ui()
            self.refresh_status()
            self.show_empty(self.results_list, tr("empty_discover"))
            self.show_empty(self.installed_list, tr("loading_installed"))
            self.load_installed()
            self.refresh_package_databases()
            if not args.skip_admin:
                self.prepare_admin()

        def build_ui(self) -> None:
            root = QWidget()
            root.setObjectName("root")
            self.setCentralWidget(root)
            main = QVBoxLayout(root)
            main.setContentsMargins(24, 22, 24, 24)
            main.setSpacing(16)

            header = QHBoxLayout()
            header.setSpacing(12)
            main.addLayout(header)

            mark = QLabel()
            mark.setObjectName("brandMark")
            mark.setFixedSize(58, 58)
            mark.setAlignment(align_center)
            if ICON_SOURCE.exists():
                pixmap = QPixmap(str(ICON_SOURCE))
                if not pixmap.isNull():
                    mark.setPixmap(pixmap.scaled(54, 54))
            header.addWidget(mark)

            brand = QVBoxLayout()
            brand.setSpacing(1)
            header.addLayout(brand)
            title = QLabel(tr("title"))
            title.setObjectName("brandTitle")
            brand.addWidget(title)
            subtitle = QLabel(tr("tagline"))
            subtitle.setObjectName("muted")
            brand.addWidget(subtitle)

            self.search_entry = QLineEdit()
            self.search_entry.setObjectName("searchEntry")
            self.search_entry.setPlaceholderText(tr("search_placeholder"))
            self.search_entry.returnPressed.connect(self.search_all_sources)
            self.search_entry.textChanged.connect(self.on_search_text_changed)
            header.addWidget(self.search_entry, 1)

            search_button = QPushButton(tr("search"))
            search_button.setProperty("role", "primary")
            search_button.clicked.connect(self.search_all_sources)
            header.addWidget(search_button)

            self.only_gui_check = QCheckBox(tr("apps_only"))
            self.only_gui_check.setChecked(True)
            self.only_gui_check.stateChanged.connect(self.on_gui_filter_changed)
            header.addWidget(self.only_gui_check)

            self.language_combo = QComboBox()
            self.language_combo.addItem("Deutsch", "de")
            self.language_combo.addItem("English", "en")
            self.language_combo.setCurrentIndex(0 if LANGUAGE == "de" else 1)
            self.language_combo.currentIndexChanged.connect(self.on_language_changed)
            header.addWidget(QLabel(tr("language")))
            header.addWidget(self.language_combo)

            self.frontend_combo = QComboBox()
            for value, label in (("auto", tr("frontend_auto")), ("qt", tr("frontend_qt")), ("gtk", tr("frontend_gtk"))):
                self.frontend_combo.addItem(label, value)
            preference = core.frontend_preference()
            for index in range(self.frontend_combo.count()):
                if self.frontend_combo.itemData(index) == preference:
                    self.frontend_combo.setCurrentIndex(index)
                    break
            self.frontend_combo.currentIndexChanged.connect(self.on_frontend_changed)
            header.addWidget(QLabel(tr("frontend")))
            header.addWidget(self.frontend_combo)

            self.tabs = QTabWidget()
            self.tabs.currentChanged.connect(self.on_tab_changed)
            main.addWidget(self.tabs, 1)

            self.results_title = QLabel(tr("discover"))
            self.results_title.setObjectName("sectionTitle")
            self.results_list = QListWidget()
            self.results_list.setSelectionMode(QListWidget.SelectionMode.NoSelection if hasattr(QListWidget, "SelectionMode") else QListWidget.NoSelection)
            self.tabs.addTab(self.make_list_page(self.results_title, self.results_list), tr("discover"))

            self.installed_title = QLabel(tr("installed"))
            self.installed_title.setObjectName("sectionTitle")
            self.installed_meta = QLabel("")
            self.installed_meta.setObjectName("muted")
            self.installed_list = QListWidget()
            self.installed_list.setSelectionMode(QListWidget.SelectionMode.NoSelection if hasattr(QListWidget, "SelectionMode") else QListWidget.NoSelection)
            self.tabs.addTab(self.make_installed_page(), tr("installed"))

            self.updates_meta = QLabel("")
            self.updates_meta.setObjectName("muted")
            self.updates_list = QListWidget()
            self.updates_list.setSelectionMode(QListWidget.SelectionMode.NoSelection if hasattr(QListWidget, "SelectionMode") else QListWidget.NoSelection)
            self.tabs.addTab(self.make_updates_page(), tr("updates"))

            self.tabs.addTab(self.make_manual_page(), tr("manual"))

            self.source_chips = QHBoxLayout()
            self.source_chips.setSpacing(7)
            main.insertLayout(1, self.source_chips)

        def rebuild_ui(self) -> None:
            query = self.search_entry.text()
            only_gui = self.only_gui_check.isChecked()
            tab = self.tabs.currentIndex()
            self._suspend_events = True
            self.build_ui()
            self.search_entry.setText(query)
            self.only_gui_check.setChecked(only_gui)
            self.tabs.setCurrentIndex(tab)
            self.render_source_chips()
            self.render_results()
            self.render_installed()
            self.render_updates()
            self._suspend_events = False

        def make_list_page(self, title: Any, list_widget: Any) -> Any:
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setSpacing(12)
            layout.addWidget(title)
            layout.addWidget(list_widget, 1)
            return page

        def make_installed_page(self) -> Any:
            page = QWidget()
            layout = QVBoxLayout(page)
            top = QHBoxLayout()
            layout.addLayout(top)
            top.addWidget(self.installed_title)
            top.addWidget(self.installed_meta)
            top.addStretch(1)
            refresh = QPushButton(tr("refresh"))
            refresh.setProperty("role", "secondary")
            refresh.clicked.connect(self.load_installed)
            top.addWidget(refresh)
            layout.addWidget(self.installed_list, 1)
            return page

        def make_updates_page(self) -> Any:
            page = QWidget()
            layout = QVBoxLayout(page)
            top = QHBoxLayout()
            layout.addLayout(top)
            title = QLabel(tr("updates"))
            title.setObjectName("sectionTitle")
            top.addWidget(title)
            top.addWidget(self.updates_meta)
            top.addStretch(1)
            refresh = QPushButton(tr("refresh"))
            refresh.setProperty("role", "secondary")
            refresh.clicked.connect(self.load_updates)
            top.addWidget(refresh)
            update_all = QPushButton(tr("update_all"))
            update_all.setProperty("role", "primary")
            update_all.clicked.connect(self.update_all_sources)
            top.addWidget(update_all)
            layout.addWidget(self.updates_list, 1)
            return page

        def make_manual_page(self) -> Any:
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setSpacing(14)
            title = QLabel(tr("manual_install"))
            title.setObjectName("sectionTitle")
            layout.addWidget(title)

            grid = QGridLayout()
            grid.setSpacing(16)
            layout.addLayout(grid)

            appimage = self.panel()
            app_layout = QFormLayout(appimage)
            app_layout.setSpacing(10)
            self.appimage_name = QLineEdit()
            self.appimage_name.setPlaceholderText("Obsidian")
            self.appimage_path = PathField("/home/user/Downloads/App.AppImage")
            self.appimage_icon = PathField("/home/user/Pictures/logo.png")
            app_layout.addRow(QLabel("Name"), self.appimage_name)
            app_layout.addRow(QLabel(tr("appimage_file")), self.appimage_path)
            app_layout.addRow(QLabel(tr("desktop_launcher_logo")), self.appimage_icon)
            app_button = QPushButton(tr("install_appimage"))
            app_button.setProperty("role", "primary")
            app_button.clicked.connect(self.install_appimage)
            app_layout.addRow(app_button)
            grid.addWidget(appimage, 0, 0)

            archive = self.panel()
            archive_layout = QFormLayout(archive)
            archive_layout.setSpacing(10)
            self.archive_name = QLineEdit()
            self.archive_name.setPlaceholderText("Toolbox")
            self.archive_path = PathField("/home/user/Downloads/tool.tar.gz")
            self.archive_executable = QLineEdit()
            self.archive_executable.setPlaceholderText("bin/tool")
            self.archive_icon = PathField("/home/user/Pictures/icon.svg")
            archive_layout.addRow(QLabel("Name"), self.archive_name)
            archive_layout.addRow(QLabel(tr("archive_file")), self.archive_path)
            archive_layout.addRow(QLabel(tr("executable_inside_archive")), self.archive_executable)
            archive_layout.addRow(QLabel(tr("desktop_launcher_logo")), self.archive_icon)
            archive_button = QPushButton(tr("install_archive"))
            archive_button.setProperty("role", "primary")
            archive_button.clicked.connect(self.install_archive)
            archive_layout.addRow(archive_button)
            grid.addWidget(archive, 0, 1)

            source = self.panel()
            source_layout = QFormLayout(source)
            source_layout.setSpacing(10)
            self.source_manager_combo = QComboBox()
            for source_id, label in SOURCES:
                if source_id in core.SYSTEM_SOURCE_ORDER:
                    self.source_manager_combo.addItem(label, source_id)
            native_source = core.native_package_source()
            for index in range(self.source_manager_combo.count()):
                if self.source_manager_combo.itemData(index) == native_source:
                    self.source_manager_combo.setCurrentIndex(index)
                    break
            self.source_name = QLineEdit()
            self.source_name.setPlaceholderText("vendor-tools")
            self.source_url = QLineEdit()
            self.source_url.setPlaceholderText("https://repo.example.com/packages")
            self.source_key_url = QLineEdit()
            self.source_key_url.setPlaceholderText("https://repo.example.com/signing-key.gpg")
            self.source_distribution = QLineEdit(core.os_release_codename() or "stable")
            self.source_components = QLineEdit("main")
            source_layout.addRow(QLabel(tr("manager")), self.source_manager_combo)
            source_layout.addRow(QLabel(tr("source_name")), self.source_name)
            source_layout.addRow(QLabel(tr("source_url")), self.source_url)
            source_layout.addRow(QLabel(tr("key_url")), self.source_key_url)
            source_layout.addRow(QLabel(tr("distribution")), self.source_distribution)
            source_layout.addRow(QLabel(tr("components")), self.source_components)
            source_button = QPushButton(tr("add_source"))
            source_button.setProperty("role", "primary")
            source_button.clicked.connect(self.add_package_source)
            source_layout.addRow(source_button)
            grid.addWidget(source, 1, 0, 1, 2)

            layout.addStretch(1)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            return scroll

        def panel(self) -> Any:
            frame = QFrame()
            frame.setObjectName("panel")
            frame.setSizePolicy(QSizePolicy.Policy.Expanding if hasattr(QSizePolicy, "Policy") else QSizePolicy.Expanding, QSizePolicy.Policy.Preferred if hasattr(QSizePolicy, "Policy") else QSizePolicy.Preferred)
            return frame

        def run_async(self, fn: Callable[[], Any], callback: Callable[[Any, Exception | None], None]) -> None:
            call = AsyncCall(fn, callback)
            self._async_calls.append(call)

            def cleanup(result: Any, error: object) -> None:
                callback(result, error if isinstance(error, Exception) else None)
                if call in self._async_calls:
                    self._async_calls.remove(call)

            call.finished.disconnect()
            call.finished.connect(cleanup)
            call.start()

        def on_language_changed(self) -> None:
            if self._suspend_events:
                return
            language = self.language_combo.currentData()
            if language and language != LANGUAGE:
                set_language(str(language))
                self.rebuild_ui()

        def on_frontend_changed(self) -> None:
            if self._suspend_events:
                return
            preference = str(self.frontend_combo.currentData() or "auto")
            if preference == core.frontend_preference():
                return
            core.set_frontend_preference(preference)
            QMessageBox.information(self, tr("frontend"), tr("frontend_restart"))

        def on_tab_changed(self, index: int) -> None:
            if index == 1:
                self.render_installed()
            elif index == 2:
                if self.only_gui_check.isChecked():
                    self.only_gui_check.setChecked(False)
                self.render_updates()
                if not self.updates:
                    self.load_updates()

        def on_search_text_changed(self) -> None:
            if self._suspend_events:
                return
            if self.tabs.currentIndex() == 1:
                self.render_installed()
            elif self.tabs.currentIndex() == 2:
                self.render_updates()

        def on_gui_filter_changed(self) -> None:
            if self._suspend_events:
                return
            self.render_installed()
            self.render_updates()
            if self.tabs.currentIndex() == 0 and len(self.search_entry.text().strip()) >= 2:
                self.search_all_sources()

        def refresh_status(self) -> None:
            def done(data: Any, error: Exception | None) -> None:
                if error:
                    self.log(tr("source_status_failed", error=error))
                    return
                self.status_data = data
                self.render_source_chips()

            self.run_async(core.status, done)

        def refresh_package_databases(self) -> None:
            source = core.native_package_source()
            if not source:
                return
            try:
                self.refreshing_metadata_sources.add(source)
                self.pending_update_sources.add(source)
                label, command = core.refresh_metadata_command(source)
                job = core.start_job(label, command)
                self.watch_job(job.id, update_source=source, refresh_status_after=True, show_failure_dialog=False)
            except Exception as exc:  # noqa: BLE001 - best-effort background task
                self.pending_update_sources.discard(source)
                self.refreshing_metadata_sources.discard(source)
                self.log(str(exc))

        def render_source_chips(self) -> None:
            while self.source_chips.count():
                item = self.source_chips.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            sources = self.status_data.get("sources", {}) if self.status_data else {}
            installable_managers = {str(tool.get("id")): str(tool.get("name")) for tool in core.package_manager_tools()}
            for source_id, label in SOURCES:
                meta = sources.get(source_id, {})
                if source_id in self.pending_manager_installs and source_id in installable_managers:
                    chip = QLabel(f"{installable_managers[source_id]}: {tr('installing_now')}")
                elif not meta.get("available") and source_id in installable_managers:
                    manager_name = installable_managers[source_id]
                    chip = QPushButton(tr("install_missing_manager_chip", name=manager_name))
                    chip.clicked.connect(lambda _checked=False, selected=source_id, name=manager_name: self.offer_install_manager_tool(selected, name))
                else:
                    chip = QLabel(f"{label}: {tr('ready') if meta.get('available') else tr('missing')}")
                chip.setObjectName("chip")
                chip.setProperty("off", not meta.get("available"))
                self.source_chips.addWidget(chip)
            self.source_chips.addStretch(1)

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

        def clear_list(self, list_widget: Any) -> None:
            list_widget.clear()

        def show_empty(self, list_widget: Any, text: str) -> None:
            list_widget.clear()
            item = QListWidgetItem(text)
            item.setFlags(item.flags() & ~2)
            list_widget.addItem(item)

        def add_row(self, list_widget: Any, row: Any) -> None:
            item = QListWidgetItem()
            item.setSizeHint(row.sizeHint())
            list_widget.addItem(item)
            list_widget.setItemWidget(item, row)

        def search_all_sources(self) -> None:
            query = self.search_entry.text().strip()
            self.tabs.setCurrentIndex(0)
            if len(query) < 2:
                self.show_empty(self.results_list, tr("min_chars"))
                return
            self.search_token += 1
            token = self.search_token
            self.results = []
            include_non_gui = not self.only_gui_check.isChecked()
            mode = tr("mode_all") if include_non_gui else tr("mode_gui")
            self.show_empty(self.results_list, tr("searching", mode=mode))
            self.results_title.setText(tr("search_results", query=query))
            self.log(tr("search_started", query=query, mode=mode))

            def done(items: Any, error: Exception | None) -> None:
                if token != self.search_token:
                    return
                if error:
                    self.show_empty(self.results_list, tr("search_failed", error=error))
                    self.log(tr("search_failed", error=error))
                    return
                self.results = items
                if not self.results:
                    self.show_empty(self.results_list, tr("no_results"))
                else:
                    self.render_results()
                self.log(tr("search_finished", count=len(self.results)))

            self.run_async(lambda: core.search_all_packages(query, include_non_gui=include_non_gui), done)

        def render_results(self) -> None:
            self.clear_list(self.results_list)
            if not self.results:
                self.show_empty(self.results_list, tr("empty_discover"))
                return
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
                self.add_row(self.results_list, row)

        def load_installed(self) -> None:
            def done(items: Any, error: Exception | None) -> None:
                if error:
                    self.log(str(error))
                    self.show_empty(self.installed_list, tr("installed_load_failed"))
                    return
                self.installed = items
                self.installed_keys = {key for key in (self.package_key(item) for item in self.installed) if key[1]}
                self.render_installed()
                if self.results:
                    self.render_results()

            self.run_async(lambda: core.list_installed("all"), done)

        def render_installed(self) -> None:
            query = self.search_entry.text().strip().lower() if self.tabs.currentIndex() == 1 else ""
            visible_installed = [item for item in self.installed if item.get("source") != "desktop"]
            items = visible_installed
            if self.only_gui_check.isChecked():
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
            self.installed_meta.setText(tr("entries_count", count=len(items), total=len(visible_installed)))
            if not items:
                self.show_empty(self.installed_list, tr("no_installed"))
                return
            self.clear_list(self.installed_list)
            for item in sorted(items, key=lambda value: (value.get("source", ""), value.get("name", "").lower())):
                self.add_row(self.installed_list, PackageRow(item, tr("remove"), "danger", self.uninstall_package))

        def load_updates(self) -> None:
            if self.updates_loading:
                return
            self.updates_loading = True
            if self.updates:
                self.render_updates()
            else:
                self.show_empty(self.updates_list, tr("checking_updates"))

            def done(items: Any, error: Exception | None) -> None:
                self.updates_loading = False
                if error:
                    self.log(tr("updates_check_failed", error=error))
                    if self.updates:
                        self.render_updates()
                    else:
                        self.show_empty(self.updates_list, tr("updates_check_failed", error=error))
                    return
                self.updates = items
                self.render_updates()

            self.run_async(lambda: core.list_all_updates(include_non_gui=True), done)

        def visible_updates(self) -> list[dict[str, Any]]:
            items = self.updates
            return items

        def render_updates(self) -> None:
            items = self.visible_updates()
            if self.updates_loading:
                meta = tr("updates_found", count=len(items)) if items else ""
                self.updates_meta.setText(f"{meta} - {tr('checking_updates')}" if meta else tr("checking_updates"))
            else:
                self.updates_meta.setText(tr("updates_found", count=len(items)) if items else "")
            if not items:
                if self.updates_loading:
                    message = tr("checking_updates")
                else:
                    message = tr("updating_now") if self.pending_update_sources else tr("no_updates")
                self.show_empty(self.updates_list, message)
                return
            self.clear_list(self.updates_list)
            for item in items:
                row = PackageRow(item, tr("update"), "primary", self.update_package)
                pending = self.pending_update_packages.get(self.package_key(item))
                if pending or item.get("source") in self.pending_update_sources:
                    row.set_busy(tr("updating_now"))
                self.add_row(self.updates_list, row)

        def install_package(self, item: dict[str, Any], row: PackageRow) -> None:
            package_key = self.package_key(item)
            self.pending_actions[package_key] = "install"
            row.set_busy(tr("installing_now"))
            source = item.get("source", "")
            name = item.get("packageName") or item.get("id") or item.get("name", "")
            try:
                label, command = core.install_command(source, name)
                job = core.start_job(label, command)
                self.watch_job(job.id, package_key=package_key)
            except Exception as exc:  # noqa: BLE001
                self.pending_actions.pop(package_key, None)
                row.clear_busy()
                self.show_error_details(str(exc), str(exc))

        def uninstall_package(self, item: dict[str, Any], row: PackageRow) -> None:
            package_key = self.package_key(item)
            self.pending_actions[package_key] = "remove"
            row.set_busy(tr("removing_now"))
            source = item.get("source", "")
            name = item.get("packageName") or item.get("id") or item.get("name", "")
            if source == "manual":
                def done(_entry: Any, error: Exception | None) -> None:
                    self.pending_actions.pop(package_key, None)
                    if error:
                        self.show_error_details(tr("removal_failed", error=error), str(error))
                    else:
                        self.log(tr("removed", name=name))
                        self.load_installed()
                    if self.results:
                        self.render_results()

                self.run_async(lambda: core.uninstall_manual(str(name)), done)
                return
            try:
                label, command = core.uninstall_command(source, name)
                job = core.start_job(label, command)
                self.watch_job(job.id, package_key=package_key)
            except Exception as exc:  # noqa: BLE001
                self.pending_actions.pop(package_key, None)
                row.clear_busy()
                self.show_error_details(str(exc), str(exc))

        def update_package(self, item: dict[str, Any], row: PackageRow | None = None) -> None:
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
                self.watch_job(job.id, update_package=package_key)
            except Exception as exc:  # noqa: BLE001
                self.pending_update_packages.pop(package_key, None)
                if row:
                    row.clear_busy()
                self.show_error_details(tr("update_failed", error=exc), str(exc))

        def update_all_sources(self) -> None:
            sources = self.status_data.get("sources", {}) if self.status_data else {}
            queued = [
                source
                for source, _label in SOURCES
                if source not in {"manual", "desktop"}
                and sources.get(source, {}).get("available")
                and source not in self.pending_update_sources
            ]
            self.batch_update_sources = set(queued)
            self.update_source_queue.extend(queued)
            self.start_next_queued_update_source()

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
            except Exception as exc:  # noqa: BLE001
                self.pending_update_sources.discard(source)
                self.batch_update_sources.discard(source)
                self.render_updates()
                self.show_error_details(tr("update_failed", error=exc), str(exc))
                if continue_queue:
                    self.start_next_queued_update_source()

        def add_package_source(self) -> None:
            payload = {
                "manager": self.source_manager_combo.currentData(),
                "name": self.source_name.text().strip(),
                "url": self.source_url.text().strip(),
                "keyUrl": self.source_key_url.text().strip(),
                "distribution": self.source_distribution.text().strip(),
                "components": self.source_components.text().strip(),
            }
            try:
                label, command = core.add_package_source_command(payload)
                job = core.start_job(label, command)
                self.log(tr("add_source_started", name=payload["name"]))
                self.watch_job(job.id, refresh_status_after=True)
            except Exception as exc:  # noqa: BLE001
                self.show_error_details(tr("add_source_failed", error=exc), str(exc))

        def offer_install_manager_tool(self, tool_id: str, name: str) -> None:
            answer = QMessageBox.question(self, tr("install_manager"), tr("install_missing_manager_prompt", name=name))
            yes_value = QMessageBox.StandardButton.Yes if hasattr(QMessageBox, "StandardButton") else QMessageBox.Yes
            if answer == yes_value:
                self.install_manager_tool(tool_id, name)

        def install_manager_tool(self, tool_id: str, name: str) -> None:
            self.pending_manager_installs.add(tool_id)
            self.render_source_chips()
            try:
                label, command = core.install_package_manager_command(tool_id)
                job = core.start_job(label, command)
                self.log(tr("install_manager_started", name=name))
                self.watch_job(job.id, manager_tool=tool_id)
            except Exception as exc:  # noqa: BLE001
                self.pending_manager_installs.discard(tool_id)
                self.render_source_chips()
                self.show_error_details(tr("install_manager_failed", error=exc), str(exc))

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
            timer = QTimer(self)

            def poll() -> None:
                nonlocal last_len
                job = core.JOBS.get(job_id)
                if not job:
                    timer.stop()
                    return
                for line in job.output[last_len:]:
                    self.log(line)
                last_len = len(job.output)
                if job.state not in {"done", "failed"}:
                    return
                timer.stop()
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
                    self.show_error_details(tr("job_failed", label=job.label, code=job.exit_code), details)
                if job.state == "done" and manager_tool:
                    tool = next((item for item in core.package_manager_tools() if str(item.get("id")) == manager_tool), None)
                    if tool and not tool.get("installed"):
                        self.show_error_details(tr("install_manager_missing_after", name=str(tool.get("name") or manager_tool)), details)
                if self.results:
                    self.render_results()
                self.load_installed()
                if update_package:
                    self.load_updates()
                if update_source:
                    if self.update_source_queue:
                        self.start_next_queued_update_source()
                    else:
                        self.load_updates()
                        if self.batch_update_errors:
                            details = "\n\n".join(self.batch_update_errors)
                            self.batch_update_errors = []
                            self.show_error_details(tr("update_failed", error="one or more package managers failed"), details)

            timer.timeout.connect(poll)
            timer.start(700)

        def install_appimage(self) -> None:
            payload = {
                "name": self.appimage_name.text().strip(),
                "appimagePath": self.appimage_path.text(),
                "iconPath": self.appimage_icon.text(),
            }

            def done(entry: Any, error: Exception | None) -> None:
                if error:
                    self.show_error_details(tr("appimage_failed", error=error), str(error))
                else:
                    self.log(tr("appimage_installed", name=entry.get("name")))
                    self.load_installed()

            self.run_async(lambda: core.install_appimage(payload), done)

        def install_archive(self) -> None:
            payload = {
                "name": self.archive_name.text().strip(),
                "archivePath": self.archive_path.text(),
                "executable": self.archive_executable.text().strip(),
                "iconPath": self.archive_icon.text(),
            }

            def done(entry: Any, error: Exception | None) -> None:
                if error:
                    self.show_error_details(tr("archive_failed", error=error), str(error))
                else:
                    self.log(tr("archive_installed", name=entry.get("name")))
                    self.load_installed()

            self.run_async(lambda: core.install_archive(payload), done)

        def show_error_details(self, title: str, details: str) -> None:
            dialog = QDialog(self)
            dialog.setWindowTitle(tr("error_details"))
            dialog.resize(720, 420)
            layout = QVBoxLayout(dialog)
            label = QLabel(title)
            label.setWordWrap(True)
            label.setObjectName("packageName")
            layout.addWidget(label)
            text = QTextEdit()
            text.setReadOnly(True)
            text.setPlainText(details)
            layout.addWidget(text, 1)
            close = QPushButton(tr("close"))
            close.setProperty("role", "secondary")
            close.clicked.connect(dialog.close)
            layout.addWidget(close, 0, align_right)
            dialog.exec()

        def prepare_admin(self) -> None:
            def admin() -> str:
                if os.geteuid() == 0:
                    return tr("admin_already_root")
                if core.which("pkexec"):
                    proc = subprocess.run(["pkexec", "true"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=180)
                    if proc.returncode == 0:
                        return tr("admin_authorized")
                    return tr("admin_not_confirmed")
                if core.sudo_askpass_ready():
                    proc = subprocess.run(["sudo", "-A", "-v"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=180)
                    if proc.returncode == 0:
                        return tr("admin_sudo_authorized")
                    return tr("admin_sudo_not_confirmed")
                if core.which("sudo"):
                    return tr("sudo_askpass_unsupported")
                return tr("unknown_admin")

            def done(message: Any, error: Exception | None) -> None:
                self.log(str(error or message))

            self.log(tr("admin_prepare"))
            self.run_async(admin, done)

    app = QApplication([sys.argv[0]])
    app.setApplicationName(APP_TITLE)
    app.setDesktopFileName(APP_ID)
    app.setStyleSheet(
        """
        QWidget#root { background: #f6f4ef; color: #1d2528; font-family: Inter, Cantarell, Sans-Serif; }
        QLabel#brandTitle { font-size: 20px; font-weight: 900; }
        QLabel#sectionTitle { font-size: 30px; font-weight: 900; }
        QLabel#muted, QLabel#meta { color: #687477; }
        QLabel#meta { font-size: 12px; font-weight: 700; }
        QLineEdit#searchEntry { min-height: 44px; border-radius: 8px; border: 1px solid #d8d2c6; background: #fffdf8; padding: 0 12px; font-size: 15px; }
        QPushButton { min-height: 34px; border-radius: 8px; padding: 6px 14px; font-weight: 800; border: 1px solid #d8d2c6; background: #fffdf8; }
        QPushButton[role="primary"] { background: #0f766e; color: #f8fffd; border: 1px solid #0f766e; }
        QPushButton[role="secondary"] { background: #e8eef4; color: #285f9f; border: 1px solid #ccd9e8; }
        QPushButton[role="danger"] { background: #f4e2df; color: #b13d35; border: 1px solid #e8c4bf; }
        QLabel#chip, QPushButton#chip { border: 1px solid #d8d2c6; border-radius: 12px; padding: 5px 9px; background: #fffdf8; font-size: 12px; font-weight: 800; color: #445053; }
        QLabel#chip[off="true"], QPushButton#chip[off="true"] { color: #916012; background: #fbefd8; }
        QLabel#packageIcon { background: #e0f2ef; color: #0b4f49; border-radius: 8px; font-weight: 900; }
        QLabel#packageName { font-size: 15px; font-weight: 900; }
        QFrame#panel { background: #fffdf8; border: 1px solid #d8d2c6; border-radius: 8px; padding: 14px; }
        QListWidget { background: transparent; border: 0; }
        QListWidget::item { background: #fffdf8; border: 1px solid #d8d2c6; border-radius: 8px; margin: 5px 0; }
        QTabWidget::pane { border: 0; }
        QTabBar::tab { min-height: 34px; padding: 6px 18px; border-radius: 6px; background: #ece7dc; color: #687477; font-weight: 800; }
        QTabBar::tab:selected { background: #fffdf8; color: #1d2528; }
        """
    )
    window = MainWindow()
    window.show()
    return app.exec()


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
        binding = load_qt().get("binding", "Qt")
        print(f"{binding} ok")
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
    return run_qt_app(args)


if __name__ == "__main__":
    raise SystemExit(main())
