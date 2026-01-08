#!/usr/bin/env python3
"""
Minimal installer for OSS Audit (pyproject-only, ASCII output).

Usage:
  python scripts/install_deps.py --env dev     # install project with dev extras
  python scripts/install_deps.py --env prod    # install project only
  python scripts/install_deps.py --env full    # same as dev for now
  python scripts/install_deps.py --no-pre-commit
"""

import argparse
import subprocess
import sys


def run(cmd: str, desc: str) -> None:
    print(f"-- {desc} ...")
    subprocess.run(cmd, shell=True, check=True)
    print(f"   OK: {desc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install OSS Audit dependencies")
    parser.add_argument("--env", choices=["prod", "dev", "full"], default="dev")
    parser.add_argument("--no-pre-commit", action="store_true")
    args = parser.parse_args()

    try:
        run("python -m pip install --upgrade pip", "upgrade pip")
        if args.env == "prod":
            run("pip install -e .", "install project (prod)")
        else:  # dev/full
            run("pip install -e .[dev]", "install project with dev extras")

        if not args.no_pre_commit and args.env in ("dev", "full"):
            try:
                run("pre-commit install", "install pre-commit hooks")
            except subprocess.CalledProcessError:
                print("   WARN: pre-commit not available; skip hooks")

        print("-- Done. Try: make quick-check")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

