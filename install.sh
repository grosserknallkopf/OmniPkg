#!/usr/bin/env bash
set -euo pipefail

APP_NAME="OmniPkg"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA_HOME/omnipkg"
LEGACY_APP_DIR="$DATA_HOME/arch-software-manager"
BIN_DIR="$HOME/.local/bin"
BIN_FILE="$BIN_DIR/omnipkg"
LEGACY_BIN_FILES=("$BIN_DIR/arch-software-manager" "$BIN_DIR/arch_software_manager")
SUDOERS_FILE="/etc/sudoers.d/omnipkg"
GITHUB_REPO_URL="https://github.com/grosserknallkopf/OmniPkg.git"
AUTOUPDATE_FILE="$BIN_DIR/omnipkg-autoupdate"
CONFIGURE_SUDOERS=1
INSTALL_DEPS=1
KEEP_SOURCE=0
CONFIGURE_CRON=1

for arg in "$@"; do
  case "$arg" in
    --no-sudoers) CONFIGURE_SUDOERS=0 ;;
    --no-cron) CONFIGURE_CRON=0 ;;
    --skip-deps) INSTALL_DEPS=0 ;;
    --keep-source) KEEP_SOURCE=1 ;;
    --help)
      printf '%s\n' "Usage: ./install.sh [--no-sudoers] [--no-cron] [--skip-deps] [--keep-source]"
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$arg" >&2
      exit 2
      ;;
  esac
done

as_root() {
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    printf 'sudo is missing. Root steps cannot be executed.\n' >&2
    return 1
  fi
}

python_check() {
  python3 - <<'PY'
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
for module in ("PyQt6", "PySide6", "PyQt5", "PySide2"):
    try:
        __import__(module)
        break
    except ImportError:
        pass
else:
    raise SystemExit(1)
PY
}

install_dependencies() {
  if python_check >/dev/null 2>&1 && command -v git >/dev/null 2>&1; then
    printf 'GTK4, Qt Python bindings and git are available.\n'
    return
  fi

  printf 'Installing desktop dependencies for %s...\n' "$APP_NAME"
  if command -v apt-get >/dev/null 2>&1; then
    as_root apt-get update
    as_root apt-get install -y python3-gi gir1.2-gtk-4.0 python3-pyqt5 desktop-file-utils appstream git
  elif command -v dnf5 >/dev/null 2>&1; then
    as_root dnf5 install -y python3-gobject gtk4 python3-qt5 desktop-file-utils appstream git
  elif command -v dnf >/dev/null 2>&1; then
    as_root dnf install -y python3-gobject gtk4 python3-qt5 desktop-file-utils appstream git
  elif command -v zypper >/dev/null 2>&1; then
    as_root zypper --non-interactive install python3-gobject gtk4 python3-qt5 desktop-file-utils AppStream git
  elif command -v pacman >/dev/null 2>&1; then
    as_root pacman -Sy --needed --noconfirm python-gobject gtk4 python-pyqt5 desktop-file-utils appstream git
  elif command -v apk >/dev/null 2>&1; then
    as_root apk add python3 py3-gobject3 gtk4.0 py3-qt5 desktop-file-utils appstream git
  elif command -v xbps-install >/dev/null 2>&1; then
    as_root xbps-install -Sy python3-gobject gtk4 python3-PyQt5 desktop-file-utils AppStream git
  elif command -v eopkg >/dev/null 2>&1; then
    as_root eopkg -y install python3-gobject gtk-4 python3-qt5 desktop-file-utils appstream-glib git
  else
    printf 'No supported system package manager was found for automatic dependency installation.\n' >&2
    printf 'Please install Python 3, PyGObject/GTK4, PyQt/PySide, desktop-file-utils and appstream.\n' >&2
  fi
}

real_dir() {
  cd "$1" && pwd -P
}

source_is_app_dir() {
  [[ -d "$APP_DIR" ]] || return 1
  [[ "$(real_dir "$SRC_DIR")" == "$(real_dir "$APP_DIR")" ]]
}

move_project_to_app_dir() {
  if source_is_app_dir; then
    mkdir -p "$APP_DIR/assets"
    return
  fi

  local stage_parent stage_dir
  stage_parent="$(mktemp -d "$DATA_HOME/omnipkg-install.XXXXXX")"
  stage_dir="$stage_parent/omnipkg"
  mkdir -p "$stage_dir"
  cp -a "$SRC_DIR"/. "$stage_dir"/
  rm -rf "$APP_DIR"
  mv "$stage_dir" "$APP_DIR"
  rmdir "$stage_parent"
}

remove_original_source() {
  if [[ "$KEEP_SOURCE" -eq 1 ]] || source_is_app_dir; then
    return
  fi
  case "$SRC_DIR" in
    /|"$HOME"|"$HOME/.local"|"$DATA_HOME"|"$APP_DIR")
      printf 'Refusing to remove unsafe source directory: %s\n' "$SRC_DIR" >&2
      return 1
      ;;
  esac
  if [[ ! -f "$SRC_DIR/install.sh" || ! -f "$SRC_DIR/omnipkg.py" ]]; then
    printf 'Refusing to remove source directory because it does not look like OmniPkg: %s\n' "$SRC_DIR" >&2
    return 1
  fi
  rm -rf -- "$SRC_DIR"
  printf 'Project directory moved to: %s\n' "$APP_DIR"
}

install_files() {
  mkdir -p "$DATA_HOME" "$BIN_DIR"
  move_project_to_app_dir
  chmod 0755 "$APP_DIR/omnipkg.py" "$APP_DIR/install.sh"
  chmod 0755 "$APP_DIR/assets/omnipkg-askpass.py"
  rm -rf "$LEGACY_APP_DIR"
  for legacy_bin in "${LEGACY_BIN_FILES[@]}"; do
    rm -f "$legacy_bin"
  done
  rm -f "$APP_DIR/arch_software_manager.py" "$APP_DIR/arch_software_manager_desktop.py"
  rm -f "$APP_DIR/assets/arch-software-manager-askpass.py" "$APP_DIR/assets/arch-software-manager.svg"

  cat > "$BIN_FILE" <<EOF
#!/usr/bin/env sh
LOG_DIR="\${XDG_CACHE_HOME:-\$HOME/.cache}/omnipkg"
mkdir -p "\$LOG_DIR"
cd "$APP_DIR" || exit 1
exec python3 "$APP_DIR/omnipkg.py" "\$@" >> "\$LOG_DIR/omnipkg.log" 2>&1
EOF
  chmod 0755 "$BIN_FILE"
}

install_launcher() {
  python3 "$APP_DIR/omnipkg.py" --install-launcher
}

install_autoupdate_script() {
  mkdir -p "$BIN_DIR"
  cat > "$AUTOUPDATE_FILE" <<EOF
#!/usr/bin/env sh
LOG_DIR="\${XDG_CACHE_HOME:-\$HOME/.cache}/omnipkg"
LOG_FILE="\$LOG_DIR/autoupdate.log"
mkdir -p "\$LOG_DIR"
{
  printf '\\n[%s] OmniPkg background update started\\n' "\$(date -Is)"
  if command -v git >/dev/null 2>&1 && [ -d "$APP_DIR/.git" ]; then
    if ! git -C "$APP_DIR" remote get-url origin >/dev/null 2>&1; then
      git -C "$APP_DIR" remote add origin "$GITHUB_REPO_URL" || true
    fi
    git -C "$APP_DIR" fetch --quiet origin || true
    branch="\$(git -C "$APP_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || printf main)"
    git -C "$APP_DIR" pull --ff-only --quiet origin "\$branch" || git -C "$APP_DIR" pull --ff-only --quiet || true
    python3 "$APP_DIR/omnipkg.py" --install-launcher || true
  fi
  python3 "$APP_DIR/omnipkg.py" --background-refresh || true
  printf '[%s] OmniPkg background update finished\\n' "\$(date -Is)"
} >> "\$LOG_FILE" 2>&1
EOF
  chmod 0755 "$AUTOUPDATE_FILE"
  printf 'Background updater installed: %s\n' "$AUTOUPDATE_FILE"
}

configure_cron() {
  if [[ "$CONFIGURE_CRON" -ne 1 ]]; then
    printf 'Cron setup was skipped.\n'
    return
  fi
  if ! command -v crontab >/dev/null 2>&1; then
    printf 'crontab is missing; background update setup was skipped.\n'
    return
  fi

  local tmp next
  tmp="$(mktemp)"
  next="$(mktemp)"
  crontab -l > "$tmp" 2>/dev/null || true
  grep -v 'omnipkg-autoupdate' "$tmp" | grep -v 'OmniPkg background updater' > "$next" || true
  {
    cat "$next"
    printf '# OmniPkg background updater\n'
    printf '17 */6 * * * "%s"\n' "$AUTOUPDATE_FILE"
  } | crontab -
  rm -f "$tmp" "$next"
  printf 'Cron background updater installed.\n'
}

configure_sudoers() {
  if [[ "$CONFIGURE_SUDOERS" -ne 1 ]]; then
    printf 'sudoers setup was skipped.\n'
    return
  fi
  if ! command -v sudo >/dev/null 2>&1; then
    printf 'sudo is missing; sudoers setup was skipped.\n'
    return
  fi
  if ! command -v visudo >/dev/null 2>&1; then
    printf 'visudo is missing; sudoers setup was skipped.\n'
    return
  fi

  local target_user="${SUDO_USER:-$USER}"
  local commands=()
  for binary in apt-get dnf5 dnf zypper pacman apk xbps-install xbps-remove eopkg snap flatpak; do
    if command -v "$binary" >/dev/null 2>&1; then
      commands+=("$(command -v "$binary")")
    fi
  done
  if [[ "${#commands[@]}" -eq 0 ]]; then
    printf 'No system package managers were found for sudoers setup.\n'
    return
  fi

  local tmp
  tmp="$(mktemp)"
  {
    printf '# Installed by OmniPkg. Allows %s to run system package managers without another password prompt.\n' "$target_user"
    printf 'Cmnd_Alias OMNIPKG_PACKAGE_MANAGERS = '
    local first=1
    for command_path in "${commands[@]}"; do
      if [[ "$first" -eq 0 ]]; then
        printf ', '
      fi
      first=0
      printf '%s' "$command_path"
    done
    printf '\n'
    printf 'Defaults:%s env_keep += "SUDO_ASKPASS DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS"\n' "$target_user"
    printf '%s ALL=(root) NOPASSWD: OMNIPKG_PACKAGE_MANAGERS\n' "$target_user"
  } > "$tmp"

  as_root visudo -cf "$tmp"
  as_root install -m 0440 "$tmp" "$SUDOERS_FILE"
  rm -f "$tmp"
  printf 'sudoers rule installed: %s\n' "$SUDOERS_FILE"
}

main() {
  if [[ "$INSTALL_DEPS" -eq 1 ]]; then
    install_dependencies
  fi
  install_files
  install_launcher
  install_autoupdate_script
  configure_sudoers
  configure_cron
  remove_original_source
  printf '\n%s is installed.\n' "$APP_NAME"
  printf 'Project: %s\n' "$APP_DIR"
  printf 'Start: %s\n' "$BIN_FILE"
}

main
