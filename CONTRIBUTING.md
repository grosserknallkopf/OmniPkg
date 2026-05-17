# Contributing

Thanks for helping OmniPkg. The project aims to stay small, native, and honest:
one core module for package-manager behavior, thin desktop frontends, and no
hidden background service.

## Development Setup

Use Python 3.10 or newer.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

GTK and Qt bindings are usually best installed through your distribution
packages. The test suite does not import the desktop frontends, so local checks
can run without a full GUI stack.

## Checks

Run these before opening a pull request:

```bash
python -m ruff check .
python -m pytest
python -m compileall -q omnipkg.py omnipkg_core.py omnipkg_qt.py omnipkg_desktop.py assets tests
bash -n install.sh
```

GitHub Actions runs Ruff, compile checks, and tests on supported Python
versions.

## Architecture Rules

- Keep package-manager command construction and output parsing in
  `omnipkg_core.py`.
- Keep GTK and Qt code in their frontend modules. They should call the core
  instead of duplicating package-manager behavior.
- Keep tests focused on deterministic behavior: parsers, validation, command
  construction, registry handling, and archive safety.
- Avoid tests that install, remove, or update real packages.
- Prefer standard-library code in the core unless a dependency removes clear
  risk or complexity.

See `ARCHITECTURE.md` for the current boundaries.

## Pull Requests

Good pull requests are small enough to review and include the reason for the
change. When adding support for a package manager, include parser tests with
sample command output and document any privilege or trust assumptions.

For UI changes, keep both frontends in mind. A feature can land in one frontend
first, but the pull request should say so clearly.

## Security-Sensitive Changes

Be careful with:

- command construction and shell usage
- sudoers, `pkexec`, and askpass behavior
- archive extraction
- desktop launcher generation
- paths under `$HOME`, `$XDG_DATA_HOME`, and system package-manager locations

Never add a broad shell escape or a privileged command path just to make one
case easier.
