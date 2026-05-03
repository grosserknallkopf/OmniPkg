#!/usr/bin/env python3
"""Native GTK desktop shell for OmniPkg."""

from __future__ import annotations

import argparse
import os
import re
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


APP_ID = "dev.omnipkg.OmniPkg"
APP_TITLE = "OmniPkg"
ROOT = Path(__file__).resolve().parent
ICON_SOURCE = ROOT / "assets" / "omnipkg-logo.png"
ASKPASS_SCRIPT = ROOT / "assets" / "omnipkg-askpass.py"
MENU_ICON = Path.home() / ".local" / "share" / "icons" / "hicolor" / "512x512" / "apps" / "omnipkg.png"
PIXMAP_ICON = Path.home() / ".local" / "share" / "pixmaps" / "omnipkg.png"
DESKTOP_FILE = Path.home() / ".local" / "share" / "applications" / "omnipkg.desktop"
LEGACY_DESKTOP_FILE = Path.home() / ".local" / "share" / "applications" / "arch-software-manager.desktop"
BIN_FILE = Path.home() / ".local" / "bin" / "omnipkg"

SOURCES = [
    ("apt", "APT"),
    ("pacman", "Pacman"),
    ("aur", "AUR"),
    ("flatpak", "Flatpak"),
    ("snap", "Snap"),
    ("brew", "Homebrew"),
    ("npm", "npm"),
    ("pip", "pip"),
]

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

.activity {
  background: #151b1d;
  color: #dce7e4;
  min-width: 330px;
}

.activity-title {
  padding: 18px;
  border-bottom: 1px solid rgba(255,255,255,.12);
  font-weight: 800;
}

.activity-log {
  padding: 14px;
  color: #dce7e4;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.45;
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


def install_launcher() -> None:
    MENU_ICON.parent.mkdir(parents=True, exist_ok=True)
    PIXMAP_ICON.parent.mkdir(parents=True, exist_ok=True)
    DESKTOP_FILE.parent.mkdir(parents=True, exist_ok=True)
    if ICON_SOURCE.exists():
        MENU_ICON.write_bytes(ICON_SOURCE.read_bytes())
        PIXMAP_ICON.write_bytes(ICON_SOURCE.read_bytes())
    if ASKPASS_SCRIPT.exists():
        ASKPASS_SCRIPT.chmod(0o755)
    if not BIN_FILE.exists():
        BIN_FILE.parent.mkdir(parents=True, exist_ok=True)
        BIN_FILE.write_text(f'#!/usr/bin/env sh\nexec python3 "{ROOT / "omnipkg.py"}" "$@"\n', encoding="utf-8")
        BIN_FILE.chmod(0o755)
    if LEGACY_DESKTOP_FILE.exists():
        LEGACY_DESKTOP_FILE.unlink()
    desktop = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=OmniPkg\n"
        "Comment=Install and manage apps from APT, Pacman, AUR, Flatpak, Snap, Homebrew, npm, pip and AppImages\n"
        f"Exec={BIN_FILE}\n"
        f"Icon={MENU_ICON}\n"
        "Terminal=false\n"
        "Categories=Settings;PackageManager;\n"
        "StartupNotify=false\n"
    )
    DESKTOP_FILE.write_text(desktop, encoding="utf-8")
    DESKTOP_FILE.chmod(0o755)
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
    def __init__(self, item: dict[str, Any], action_label: str, action_class: str, callback: Callable[[dict[str, Any]], None]):
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

        button = Gtk.Button(label=action_label)
        button.add_css_class(action_class)
        button.connect("clicked", lambda _button: callback(item))
        box.append(button)


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
            title="Choose a file",
            transient_for=self.window,
            action=Gtk.FileChooserAction.OPEN,
            accept_label="Choose",
            cancel_label="Cancel",
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
        self.log_lines: list[str] = []
        self.search_token = 0

        self.build_ui()
        self.refresh_status()
        self.show_empty(self.results_list, "Search for software. OmniPkg will look across every available source.")
        self.show_empty(self.installed_list, "Loading installed packages...")
        self.load_installed()
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
        title = Gtk.Label(label="OmniPkg")
        title.set_xalign(0)
        title.add_css_class("brand-title")
        brand.append(title)
        subtitle = Gtk.Label(label="One roof for all your package sources")
        subtitle.set_xalign(0)
        subtitle.add_css_class("brand-subtitle")
        brand.append(subtitle)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search apps, packages, AppImages, CLI tools or libraries")
        self.search_entry.add_css_class("search-entry")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("activate", lambda _entry: self.search_all_sources())
        self.search_entry.connect("search-changed", self.on_search_changed)
        header.append(self.search_entry)

        search_button = Gtk.Button(label="Search")
        search_button.add_css_class("primary")
        search_button.connect("clicked", lambda _button: self.search_all_sources())
        header.append(search_button)

        gui_filter = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        gui_filter.set_valign(Gtk.Align.CENTER)
        header.append(gui_filter)
        gui_filter.append(Gtk.Label(label="Apps only"))
        self.only_gui_switch = Gtk.Switch()
        self.only_gui_switch.set_active(True)
        self.only_gui_switch.connect("notify::active", self.on_gui_filter_changed)
        gui_filter.append(self.only_gui_switch)

        tabs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        tabs.add_css_class("tabs")
        main.append(tabs)
        self.tab_buttons: dict[str, Gtk.Button] = {}
        for view, label in (("discover", "Discover"), ("installed", "Installed"), ("manual", "Manual")):
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

        self.results_title = Gtk.Label(label="Discover")
        self.results_title.add_css_class("section-title")
        self.results_title.set_xalign(0)
        self.results_list = Gtk.ListBox()
        self.results_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.stack.add_named(self.make_list_page(self.results_title, self.results_list), "discover")

        self.installed_title = Gtk.Label(label="Installed")
        self.installed_title.add_css_class("section-title")
        self.installed_title.set_xalign(0)
        self.installed_list = Gtk.ListBox()
        self.installed_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.stack.add_named(self.make_installed_page(), "installed")

        self.stack.add_named(self.make_manual_page(), "manual")
        self.set_view("discover")

        activity = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        activity.add_css_class("activity")
        root.append(activity)
        activity.append(Gtk.Label(label="Activity", css_classes=["activity-title"]))
        self.log_label = Gtk.Label(label="")
        self.log_label.set_xalign(0)
        self.log_label.set_yalign(0)
        self.log_label.set_wrap(True)
        self.log_label.add_css_class("activity-log")
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(self.log_label)
        activity.append(scroll)

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
        refresh = Gtk.Button(label="Refresh")
        refresh.add_css_class("secondary")
        refresh.connect("clicked", lambda _button: self.load_installed())
        top.append(refresh)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(self.installed_list)
        page.append(scroll)
        return page

    def make_manual_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        title = Gtk.Label(label="Manual installieren")
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
        self.appimage_path = PathField("AppImage file", "/home/user/Downloads/App.AppImage", self)
        self.appimage_icon = PathField("Desktop launcher logo", "/home/user/Pictures/logo.png", self)
        appimage.append(self.appimage_name)
        appimage.append(self.appimage_path)
        appimage.append(self.appimage_icon)
        appimage_button = Gtk.Button(label="Install AppImage")
        appimage_button.add_css_class("primary")
        appimage_button.connect("clicked", lambda _button: self.install_appimage())
        appimage.append(appimage_button)

        archive = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        archive.add_css_class("tool-panel")
        grid.attach(archive, 1, 0, 1, 1)
        archive.append(Gtk.Label(label="Archive", xalign=0, css_classes=["package-name"]))
        self.archive_name = TextField("Name", "Toolbox")
        self.archive_path = PathField("Archive file", "/home/user/Downloads/tool.tar.gz", self)
        self.archive_executable = TextField("Executable inside archive", "bin/tool")
        self.archive_icon = PathField("Desktop launcher logo", "/home/user/Pictures/icon.svg", self)
        archive.append(self.archive_name)
        archive.append(self.archive_path)
        archive.append(self.archive_executable)
        archive.append(self.archive_icon)
        archive_button = Gtk.Button(label="Install archive")
        archive_button.add_css_class("primary")
        archive_button.connect("clicked", lambda _button: self.install_archive())
        archive.append(archive_button)
        return page

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

    def on_search_changed(self, _entry: Gtk.SearchEntry) -> None:
        if self.current_view == "installed":
            self.render_installed()

    def on_gui_filter_changed(self, _switch: Gtk.Switch, _param: Any) -> None:
        self.render_installed()
        if self.current_view == "discover" and len(self.search_entry.get_text().strip()) >= 2:
            self.search_all_sources()

    def refresh_status(self) -> None:
        def done(data: Any, error: Exception | None) -> bool:
            if error:
                self.log(f"Source status failed: {error}")
                return False
            self.status_data = data
            self.render_source_chips()
            return False

        run_in_thread(core.status, done)

    def render_source_chips(self) -> None:
        while child := self.source_chips.get_first_child():
            self.source_chips.remove(child)
        sources = self.status_data.get("sources", {}) if self.status_data else {}
        for source_id, label in SOURCES:
            meta = sources.get(source_id, {})
            chip = Gtk.Label(label=f"{label}: {'ready' if meta.get('available') else 'missing'}")
            chip.add_css_class("chip")
            if not meta.get("available"):
                chip.add_css_class("off")
            self.source_chips.append(chip)

    def log(self, message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self.log_lines.append(f"[{stamp}] {message}")
        self.log_lines = self.log_lines[-180:]
        self.log_label.set_text("\n".join(self.log_lines))

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
            self.show_empty(self.results_list, "Please enter at least two characters.")
            return
        self.search_token += 1
        token = self.search_token
        self.results = []
        include_non_gui = not self.only_gui_switch.get_active()
        mode = "all packages" if include_non_gui else "graphical apps"
        self.show_empty(self.results_list, f"OmniPkg is searching {mode} across all available sources...")
        self.results_title.set_text(f"Search results for \"{query}\"")
        self.log(f"Search started: {query} ({mode})")

        def done(items: Any, error: Exception | None) -> bool:
            if token != self.search_token:
                return False
            if error:
                self.show_empty(self.results_list, f"Search failed: {error}")
                self.log(f"Search failed: {error}")
                return False
            self.results = items
            if not self.results:
                self.show_empty(self.results_list, "No results in the available sources.")
            else:
                self.render_results()
            self.log(f"Search finished: {len(self.results)} results")
            return False

        run_in_thread(lambda: core.search_all_packages(query, include_non_gui=include_non_gui), done)

    def render_results(self) -> None:
        self.clear_list(self.results_list)
        for item in sorted(self.results, key=lambda value: (value.get("source", ""), value.get("name", ""))):
            self.results_list.append(PackageRow(item, "Install", "primary", self.install_package))

    def load_installed(self) -> None:
        def done(items: Any, error: Exception | None) -> bool:
            if error:
                self.log(f"Installed packages could not be loaded: {error}")
                self.show_empty(self.installed_list, "Installed packages could not be loaded.")
                return False
            self.installed = items
            self.render_installed()
            return False

        run_in_thread(lambda: core.list_installed("all"), done)

    def render_installed(self) -> None:
        query = self.search_entry.get_text().strip().lower() if self.current_view == "installed" else ""
        items = self.installed
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
        self.installed_meta.set_text(f"{len(items)} of {len(self.installed)} entries")
        if not items:
            self.show_empty(self.installed_list, "No installed entries found.")
            return
        self.clear_list(self.installed_list)
        for item in sorted(items, key=lambda value: (value.get("source", ""), value.get("name", "").lower())):
            self.installed_list.append(PackageRow(item, "Remove", "danger", self.uninstall_package))

    def install_package(self, item: dict[str, Any]) -> None:
        source = item.get("source", "")
        name = item.get("packageName") or item.get("id") or item.get("name", "")
        try:
            label, command = core.install_command(source, name)
            job = core.start_job(label, command)
            self.watch_job(job.id)
        except Exception as exc:  # noqa: BLE001 - UI boundary
            self.log(str(exc))

    def uninstall_package(self, item: dict[str, Any]) -> None:
        source = item.get("source", "")
        name = item.get("packageName") or item.get("id") or item.get("name", "")
        if source == "manual":
            def done(_entry: Any, error: Exception | None) -> bool:
                if error:
                    self.log(f"Removal failed: {error}")
                else:
                    self.log(f"{name} removed")
                    self.load_installed()
                return False

            run_in_thread(lambda: core.uninstall_manual(str(name)), done)
            return
        try:
            label, command = core.uninstall_command(source, name)
            job = core.start_job(label, command)
            self.watch_job(job.id)
        except Exception as exc:  # noqa: BLE001 - UI boundary
            self.log(str(exc))

    def watch_job(self, job_id: str) -> None:
        self.log(f"Job started: {job_id}")
        last_len = 0

        def poll() -> bool:
            nonlocal last_len
            job = core.JOBS.get(job_id)
            if not job:
                self.log("Job not found.")
                return False
            for line in job.output[last_len:]:
                self.log(line)
            last_len = len(job.output)
            if job.state in {"done", "failed"}:
                self.log(f"{job.label}: {job.state} ({job.exit_code})")
                self.load_installed()
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
                self.log(f"AppImage failed: {error}")
            else:
                self.log(f"{entry.get('name')} installed")
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
                self.log(f"Archive failed: {error}")
            else:
                self.log(f"{entry.get('name')} installed")
                self.load_installed()
            return False

        run_in_thread(lambda: core.install_archive(payload), done)

    def prepare_admin(self) -> None:
        def admin() -> str:
            if os.geteuid() == 0:
                return "The app is already running with root privileges."
            if os.environ.get("SUDO_ASKPASS") and core.which("sudo"):
                proc = subprocess.run(
                    ["sudo", "-A", "-v"],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=False,
                    timeout=180,
                )
                if proc.returncode == 0:
                    return "Sudo authorization prepared."
                return "Sudo authorization was not confirmed. System packages will ask again later."
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
                    return "Admin authorization prepared."
                return "Admin authorization was not confirmed. System packages will ask again later."
            if core.which("sudo"):
                return "pkexec is missing. Install polkit/pkexec for graphical admin prompts."
            return "Neither pkexec nor sudo was found. System-wide installs cannot start."

        def done(message: Any, error: Exception | None) -> bool:
            self.log(str(error or message))
            return False

        self.log("Preparing admin authorization...")
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
    parser.add_argument("--skip-admin", action="store_true", help="Skip admin warmup")
    args = parser.parse_args()

    if args.install_launcher:
        install_launcher()
        print(f"Launcher installed: {DESKTOP_FILE}")
        return 0
    if args.check:
        print("GTK4 ok")
        print("Core ok")
        print("Sources:", ", ".join(source for source, _label in SOURCES))
        return 0

    if ASKPASS_SCRIPT.exists():
        os.environ.setdefault("SUDO_ASKPASS", str(ASKPASS_SCRIPT))

    app = SoftwareManagerApp(skip_admin=args.skip_admin)
    return app.run([sys.argv[0]])


if __name__ == "__main__":
    raise SystemExit(main())
