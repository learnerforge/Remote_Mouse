"""One-command launcher for TouchMorph.

Quick start:
  python start.py

First-time setup wizard:
  python setup.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLIENT = ROOT / "client"
CLIENT_DIST = CLIENT / "dist"
SERVER = ROOT / "server"


def _run(cmd, cwd, label):
    print(f"[TouchMorph] {label} ...")
    result = subprocess.run(cmd, cwd=cwd, shell=True)
    if result.returncode != 0:
        print(f"[TouchMorph] {label} FAILED (exit code {result.returncode})")
        sys.exit(result.returncode)
    return result


def main():
    print("[TouchMorph] Starting TouchMorph ...")
    print()

    if not (CLIENT / "node_modules").is_dir():
        _run("npm install", CLIENT, "Installing client dependencies")

    if not CLIENT_DIST.is_dir():
        _run("npm run build", CLIENT, "Building client app")

    _run(f"{sys.executable} main.py", SERVER, "Starting server")


if __name__ == "__main__":
    main()
