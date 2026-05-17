# Architecture

OmniPkg is intentionally a flat Python application. The current structure is
small enough that a package hierarchy would add more ceremony than clarity, but
the module boundaries are explicit.

## Runtime Shape

```text
omnipkg.py
  chooses GTK or Qt based on preference, desktop, distro, and availability

omnipkg_core.py
  detects package sources
  builds package-manager commands
  parses package-manager output
  tracks background jobs
  manages manual AppImage/archive registry entries
  creates desktop launchers for manual installs

omnipkg_desktop.py
  GTK 4 desktop frontend

omnipkg_qt.py
  Qt desktop frontend through PyQt/PySide compatibility loading

install.sh
  installs app files, launcher, optional dependencies, optional sudoers helper,
  and optional background updater

assets/
  logo and askpass helper
```

## Core Responsibilities

`omnipkg_core.py` is the only place that should know package-manager command
syntax. It contains detection, validation, parser, installer, updater, and job
helpers for APT, DNF, Zypper, Pacman, AUR helpers, APK, XBPS, eopkg, Flatpak,
Snap, Homebrew, npm, pipx, and manual installs.

The core uses the Python standard library so it can be imported and tested in
CI without GUI libraries. Functions that call external commands should return
plain dictionaries, lists, command arrays, or `ApiError` exceptions.

## Frontend Responsibilities

The GTK and Qt frontends own layout, widgets, translations, dialogs, and user
interaction. They should not parse package-manager output or build privileged
commands directly. When both frontends need a behavior, move it to the core.

The launcher in `omnipkg.py` is deliberately small. It saves an optional
frontend preference, resolves the best available frontend, then delegates to
that frontend's `main()`.

## Data and Files

OmniPkg stores user data under XDG-style locations:

- `$XDG_DATA_HOME/omnipkg/preferences.json`
- `$XDG_DATA_HOME/omnipkg/registry.json`
- `$HOME/.local/opt/omnipkg/appimages`
- `$HOME/.local/opt/omnipkg/apps`
- `$HOME/.local/share/applications`
- `$HOME/.local/share/icons`

Legacy `arch-software-manager` paths are read or cleaned up where needed so
existing users can migrate without manual file surgery.

## Package Operation Flow

1. The frontend asks the core for source status, installed packages, search
   results, updates, or a command for an operation.
2. The core validates user-provided names, paths, URLs, and sources.
3. The core chooses native package-manager commands, preferring PackageKit for
   APT, DNF, and Zypper where available, with native fallbacks.
4. Mutating commands are wrapped with `pkexec`, `sudo -A`, or `sudo` only when
   needed.
5. Long-running commands are tracked as jobs with output captured for the UI.

## Tests and CI

The test suite focuses on the stable, deterministic core surface:

- parser behavior for package-manager output
- validation of package names and repository URLs
- preference and registry file handling
- frontend resolution fallback behavior
- safe extraction for manual archive installs

CI runs Ruff, Python compile checks, and pytest across supported Python
versions. GUI libraries are intentionally outside the default CI path.

## Relationship to topgrade

Topgrade is an excellent CLI-first updater. Its own README describes the
problem as keeping a system up to date by detecting tools and running the
appropriate update commands. OmniPkg overlaps with that only in update
orchestration.

OmniPkg is not trying to replace topgrade for scripted, terminal-first,
cross-platform update automation. topgrade is likely the better fit when you
want one command, configuration-driven automation, remote runs, or a broad
developer-machine update sweep.

OmniPkg is focused on a different job:

- a native Linux desktop interface
- searching and installing software across available sources
- a single installed view with real app names and icons
- manual AppImage and archive installs with launcher generation
- visible install, remove, and update operations for people who do not want to
  manage everything from a terminal

The honest boundary is simple: topgrade is the stronger batch updater; OmniPkg
aims to be the calmer graphical software manager.
