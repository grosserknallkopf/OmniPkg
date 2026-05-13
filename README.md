<div align="center">
  <a href="https://github.com/grosserknallkopf/OmniPkg">
    <img src="assets/omnipkg-logo-full.png" alt="Logo"  width="150" height="150">
  </a>


# OmniPkg

### **Install it with OmniPkg. Keep it in one place.**
</div>
<br>

OmniPkg is a native Linux software manager for people who use more than one
package ecosystem. It brings distro repositories, app stores, developer package
managers and manual app installs into one calm desktop interface.

It is not tied to one distribution. OmniPkg detects what is available on the
current system and only enables the sources that can actually be used.

## Highlights

- One search across all available sources
- One installed view across all package managers
- Optional **Apps only** filter for hiding libraries, drivers, CLI tools and
  background system packages
- Real application names and icons from `.desktop` files, icon themes and
  AppStream metadata
- German UI when the system locale starts with `de`, English everywhere else
- Native GTK4 desktop app, no local browser service
- Manual AppImage and archive installation with desktop launcher generation
- Installer script for app files, launcher setup, optional sudoers setup and a
  background updater
- Background refreshes for package databases and OmniPkg self-updates from GitHub

## Supported Sources

OmniPkg uses a source only when its tools are installed.

- **APT** on Debian, Ubuntu and compatible systems via `apt-cache`, `apt-get`
  and `dpkg-query`
- **DNF** on Fedora, RHEL and compatible systems via `dnf5` or `dnf`
- **Zypper** on openSUSE and SUSE systems
- **Pacman** for Arch repositories
- **AUR** via `yay` or `paru`
- **APK** on Alpine Linux
- **XBPS** on Void Linux
- **eopkg** on Solus
- **Flatpak**
- **Snap**
- **Homebrew**
- **npm**
- **pipx** for isolated PyPI applications without breaking system Python
- **Manual installs** for AppImages and archives such as `.tar.gz`, `.tar.xz`
  and `.zip`

## Installation

Quickstart:

```bash
git clone https://github.com/grosserknallkopf/OmniPkg.git
cd OmniPkg
chmod +x install.sh
./install.sh
```

`install.sh` prints English status messages. It may ask for your password when
it installs dependencies or writes the optional sudoers helper. If you want to
install only the local app files and menu entry, use
`./install.sh --skip-deps --no-sudoers --no-cron`.

The installer moves OmniPkg to its permanent project directory:

```text
~/.local/share/omnipkg
```

That directory contains the whole project, including `install.sh` and Git
metadata when present. If you intentionally want to keep the source checkout
where it is, run:

```bash
./install.sh --keep-source
```

It also creates:

```text
~/.local/bin/omnipkg
~/.local/bin/omnipkg-autoupdate
~/.local/share/applications/dev.omnipkg.omnipkg.desktop
~/.local/share/icons/hicolor/512x512/apps/omnipkg.png
~/.local/share/pixmaps/omnipkg.png
```

By default, the installer also adds a user cron entry that runs every six hours.
The background updater refreshes system package databases and, when OmniPkg was
installed from a Git checkout, pulls fast-forward updates from:

```text
https://github.com/grosserknallkopf/OmniPkg
```

After installation, start OmniPkg from your application menu or run:

```bash
omnipkg
```

## Installer Options

Skip sudoers setup:

```bash
./install.sh --no-sudoers
```

Skip cron background update setup:

```bash
./install.sh --no-cron
```

Skip automatic dependency installation:

```bash
./install.sh --skip-deps
```

Keep the source directory after installing:

```bash
./install.sh --keep-source
```

## Admin Rights

OmniPkg intentionally runs as a normal user. That keeps AUR, npm and pipx
operations out of a permanent root context. If npm itself is installed by the
system package manager and points to a system prefix such as `/usr`, OmniPkg
uses `~/.local` for npm global packages instead of writing into
`/usr/lib/node_modules`.

For system package managers, the installer can optionally create a narrow
sudoers file at:

```text
/etc/sudoers.d/omnipkg
```

That rule allows the current user to run detected system package managers such
as `apt-get`, `dnf`, `zypper`, `pacman`, `apk`, `xbps`, `eopkg`, `snap` or
`flatpak` without another password prompt from inside OmniPkg. If you prefer not
to install that rule, use:

```bash
./install.sh --no-sudoers
```

Without the sudoers rule, OmniPkg uses a small GTK askpass dialog for `sudo -A`
or falls back to `pkexec`/`sudo` when needed.

## Updates

OmniPkg refreshes the native system package database in the background when the
app opens. The **Updates** tab can show available updates, while **Update all**
runs the native update command for each available package manager, for example
Pacman once, the AUR helper once, Flatpak once, npm once and pipx once. Batch
failures are collected into one error dialog instead of producing a stream of
popups.

## Application Names and Icons

OmniPkg reads local desktop launchers from common Linux locations:

```text
/usr/share/applications
~/.local/share/applications
/var/lib/flatpak/exports/share/applications
/var/lib/snapd/desktop/applications
```

When a package provides a graphical application, OmniPkg uses the same name and
icon that your desktop environment uses in the application menu. For search
results, OmniPkg also uses AppStream metadata when `appstreamcli` is available.

## Language

OmniPkg starts in German when the system locale begins with `de`, for example
`de_DE.UTF-8`. Every other locale uses English. You can override the language
for one launch with:

```bash
OMNIPKG_LANG=de omnipkg
OMNIPKG_LANG=en omnipkg
```

## Manual Installs

AppImages are copied to:

```text
~/.local/opt/omnipkg/appimages
```

OmniPkg makes them executable and creates a desktop launcher.

Archives are extracted to:

```text
~/.local/opt/omnipkg/apps
```

When an executable path is provided, OmniPkg also creates a symlink in
`~/.local/bin` and a desktop launcher.

Supported archive formats:

```text
.tar, .tar.gz, .tar.xz, .tar.bz2, .tgz, .txz, .tbz2, .zip
```

## Development

Run from the project directory:

```bash
python3 omnipkg.py
```

Run quick checks:

```bash
python3 omnipkg_desktop.py --check
python3 -m py_compile omnipkg_core.py omnipkg_desktop.py omnipkg.py
bash -n install.sh
```
