#!/usr/bin/env python3
"""OmniPkg launcher."""

from __future__ import annotations

import argparse
import sys

import omnipkg_core as core


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--frontend", choices=("auto", "qt", "gtk"), help="Choose the desktop frontend for this launch")
    parser.add_argument("--set-frontend", choices=("auto", "qt", "gtk"), help="Save the preferred desktop frontend")
    args, remaining = parser.parse_known_args()

    if args.set_frontend:
        core.set_frontend_preference(args.set_frontend)
        if not remaining:
            print(f"Frontend preference saved: {args.set_frontend}")
            return 0

    frontend = core.resolve_frontend(args.frontend)
    sys.argv = [sys.argv[0], *remaining]
    if frontend == "gtk":
        from omnipkg_desktop import main as selected_main
    else:
        from omnipkg_qt import main as selected_main
    return selected_main()


if __name__ == "__main__":
    raise SystemExit(main())
