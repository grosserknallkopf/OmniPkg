#!/usr/bin/env python3
"""Small GTK askpass helper for sudo -A."""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk  # noqa: E402


class AskPass(Gtk.Application):
    def __init__(self, prompt: str):
        super().__init__(application_id=None, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.prompt = prompt or "Admin password"
        self.password: str | None = None

    def do_activate(self) -> None:
        window = Gtk.ApplicationWindow(application=self, title="Admin authorization")
        window.set_default_size(420, 150)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(18)
        box.set_margin_bottom(18)
        box.set_margin_start(18)
        box.set_margin_end(18)
        window.set_child(box)

        label = Gtk.Label(label=self.prompt)
        label.set_xalign(0)
        label.set_wrap(True)
        box.append(label)

        entry = Gtk.Entry()
        entry.set_visibility(False)
        entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        entry.set_activates_default(True)
        box.append(entry)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        box.append(buttons)

        cancel = Gtk.Button(label="Cancel")
        buttons.append(cancel)

        ok = Gtk.Button(label="Confirm")
        ok.add_css_class("suggested-action")
        buttons.append(ok)
        window.set_default_widget(ok)

        def submit(_button: Gtk.Button | Gtk.Entry) -> None:
            self.password = entry.get_text()
            self.quit()

        def abort(_button: Gtk.Button) -> None:
            self.password = None
            self.quit()

        ok.connect("clicked", submit)
        entry.connect("activate", submit)
        cancel.connect("clicked", abort)
        window.connect("close-request", lambda _window: self.quit())
        window.present()


def main() -> int:
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Admin password"
    app = AskPass(prompt)
    app.run([sys.argv[0]])
    if app.password:
        sys.stdout.write(app.password + "\n")
        sys.stdout.flush()
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
