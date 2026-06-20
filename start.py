"""One-command launcher for TouchMorph.

Builds the client (if needed) and starts the server.
Run: python start.py
"""

import subprocess
import sys
import time
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
