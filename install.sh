#!/usr/bin/env bash
set -euo pipefail

APP_NAME="OmniPkg"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA_HOME/omnipkg"
BIN_DIR="$HOME/.local/bin"
BIN_FILE="$BIN_DIR/omnipkg"
SUDOERS_FILE="/etc/sudoers.d/omnipkg"
CONFIGURE_SUDOERS=1
INSTALL_DEPS=1

for arg in "$@"; do
  case "$arg" in
    --no-sudoers) CONFIGURE_SUDOERS=0 ;;
    --skip-deps) INSTALL_DEPS=0 ;;
    --help)
      printf '%s\n' "Usage: ./install.sh [--no-sudoers] [--skip-deps]"
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
PY
}

install_dependencies() {
  if python_check >/dev/null 2>&1; then
    printf 'GTK4/PyGObject is available.\n'
    return
  fi

  printf 'Installing desktop dependencies for %s...\n' "$APP_NAME"
  if command -v apt-get >/dev/null 2>&1; then
    as_root apt-get update
    as_root apt-get install -y python3-gi gir1.2-gtk-4.0 desktop-file-utils appstream
  elif command -v pacman >/dev/null 2>&1; then
    as_root pacman -Sy --needed --noconfirm python-gobject gtk4 desktop-file-utils appstream
  else
    printf 'No supported system package manager was found for automatic dependency installation.\n' >&2
    printf 'Please install Python 3, PyGObject, GTK4, desktop-file-utils and appstream.\n' >&2
  fi
}

install_files() {
  mkdir -p "$APP_DIR" "$APP_DIR/assets" "$BIN_DIR"
  install -m 0644 "$SRC_DIR/omnipkg_core.py" "$APP_DIR/omnipkg_core.py"
  install -m 0644 "$SRC_DIR/omnipkg_desktop.py" "$APP_DIR/omnipkg_desktop.py"
  install -m 0755 "$SRC_DIR/omnipkg.py" "$APP_DIR/omnipkg.py"
  install -m 0644 "$SRC_DIR/README.md" "$APP_DIR/README.md"
  install -m 0644 "$SRC_DIR/assets/omnipkg-logo.png" "$APP_DIR/assets/omnipkg-logo.png"
  install -m 0644 "$SRC_DIR/assets/omnipkg-logo-full.png" "$APP_DIR/assets/omnipkg-logo-full.png"
  install -m 0755 "$SRC_DIR/assets/omnipkg-askpass.py" "$APP_DIR/assets/omnipkg-askpass.py"
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
  for binary in apt-get pacman snap flatpak; do
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
  configure_sudoers
  printf '\n%s is installed.\n' "$APP_NAME"
  printf 'Start: %s\n' "$BIN_FILE"
}

main
