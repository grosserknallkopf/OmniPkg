<p align="center">
  <img src="assets/omnipkg-logo-full.png" alt="OmniPkg logo" width="360">
</p>

# OmniPkg

**Install it with OmniPkg. Keep it in one place.**

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
- Installer script for app files, launcher setup and optional sudoers setup

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
- **pip** through user installs with `python -m pip install --user`
- **Manual installs** for AppImages and archives such as `.tar.gz`, `.tar.xz`
  and `.zip`

## Installation

Quickstart:

```bash
git clone https://github.com/YOUR-USER/OmniPkg.git
cd OmniPkg
chmod +x install.sh
./install.sh
```

`install.sh` may ask for your password when it installs dependencies or writes
the optional sudoers helper. If you want to install only the local app files and
menu entry, use `./install.sh --skip-deps --no-sudoers`.

The installer copies OmniPkg to:

```text
~/.local/share/omnipkg
```

It also creates:

```text
~/.local/bin/omnipkg
~/.local/share/applications/dev.omnipkg.omnipkg.desktop
~/.local/share/icons/hicolor/512x512/apps/omnipkg.png
~/.local/share/pixmaps/omnipkg.png
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

Skip automatic dependency installation:

```bash
./install.sh --skip-deps
```

## Admin Rights

OmniPkg intentionally runs as a normal user. That keeps AUR, npm and pip
operations out of a permanent root context.

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

## GitHub

This directory is ready to become a GitHub repository. If you want to publish
directly from this machine, install and authenticate the GitHub CLI:

```bash
sudo pacman -S github-cli
gh auth login
```

Then create a repository and push:

```bash
git init
git add .
git commit -m "Initial OmniPkg release"
gh repo create OmniPkg --public --source=. --remote=origin --push
```
