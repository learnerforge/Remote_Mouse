"""TouchMorph Setup Wizard — interactive CLI for first-run setup.

Handles:
  - Python dependency installation
  - Node.js / npm dependency installation + client build
  - SMTP email configuration
  - Log checking
  - Starting the server

Usage:
  python setup.py          # run the interactive wizard
  python setup.py --quiet  # auto-install deps, skip prompts
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVER = ROOT / "server"
CLIENT = ROOT / "client"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"

BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

QUIET = "--quiet" in sys.argv


def heading(text):
    print(f"\n{BOLD}{CYAN}╔══ {text}{RESET}")
    print(f"{BOLD}{CYAN}╚{'═' * (len(text) + 4)}{RESET}\n")


def info(text):
    print(f"  {BLUE}ℹ{RESET} {text}")


def ok(text):
    print(f"  {GREEN}✓{RESET} {text}")


def warn(text):
    print(f"  {YELLOW}⚠{RESET} {text}")


def fail(text):
    print(f"  {RED}✗{RESET} {text}")


def run(cmd, cwd=None, label="", silent=False):
    if label:
        info(label)
    result = subprocess.run(cmd, cwd=cwd, shell=True,
                            capture_output=silent, text=True)
    if result.returncode != 0 and not silent:
        if result.stderr:
            print(result.stderr)
    return result


def confirm(prompt, default=True):
    if QUIET:
        return default
    suffix = " [Y/n]" if default else " [y/N]"
    answer = input(f"  {YELLOW}?{RESET} {prompt}{suffix} ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def prompt(prompt_text, default=""):
    if QUIET:
        return default
    d = f" [{default}]" if default else ""
    val = input(f"  {YELLOW}?{RESET} {prompt_text}{d}: ").strip()
    return val if val else default


# ─── Step 1: Python Dependencies ───────────────────────────────────────


def check_python():
    heading("Step 1: Python Dependencies")
    req_file = SERVER / "requirements.txt"
    if not req_file.exists():
        warn("requirements.txt not found, skipping")
        return True

    try:
        import pip
    except ImportError:
        fail("pip not found. Install Python and pip first.")
        return False

    info("Checking installed Python packages ...")
    result = run(f"{sys.executable} -m pip install -r \"{req_file}\"",
                 cwd=SERVER, label="Installing Python dependencies",
                 silent=QUIET)
    if result.returncode == 0:
        ok("Python dependencies installed")
        return True
    else:
        fail("Python dependency installation failed")
        return False


# ─── Step 2: Node.js & Client Build ────────────────────────────────────


def check_node():
    heading("Step 2: Client Build")
    if not shutil.which("node"):
        fail("Node.js not found. Install from https://nodejs.org/")
        return False
    ok(f"Node.js found: {subprocess.run('node --version', capture_output=True, text=True).stdout.strip()}")

    if not shutil.which("npm"):
        fail("npm not found")
        return False

    if not (CLIENT / "node_modules").is_dir():
        info("Installing client dependencies (npm install) ...")
        r = run("npm install", cwd=CLIENT, silent=QUIET)
        if r.returncode != 0:
            fail("npm install failed")
            return False
        ok("Client dependencies installed")
    else:
        ok("Client dependencies already installed")

    dist = CLIENT / "dist"
    if not dist.is_dir() or not list(dist.iterdir()):
        info("Building client app (npm run build) ...")
        r = run("npm run build", cwd=CLIENT, silent=QUIET)
        if r.returncode != 0:
            fail("Client build failed")
            return False
        ok("Client app built")

    return True


# ─── Step 3: Email Configuration ────────────────────────────────────────


def configure_email():
    heading("Step 3: Email Registration")

    if confirm("Configure SMTP email for tunnel URL delivery?", default=True):
        smtp_host = prompt("SMTP host", "smtp.gmail.com")
        smtp_port = prompt("SMTP port", "587")
        smtp_user = prompt("SMTP username (full email)")
        smtp_pass = prompt("SMTP app password")
        email_from = prompt("From email", smtp_user)
        email_to = prompt("Send tunnel URL to")

        lines = []
        if ENV_FILE.exists():
            lines = ENV_FILE.read_text(encoding="utf-8").splitlines(keepends=True)

        # Remove existing SMTP lines
        lines = [l for l in lines if not l.startswith(("SMTP_", "EMAIL_"))]

        smtp_lines = [
            f"\n# SMTP Email (configured by setup.py)\n",
            f"SMTP_HOST={smtp_host}\n",
            f"SMTP_PORT={smtp_port}\n",
            f"SMTP_USER={smtp_user}\n",
            f"SMTP_PASS={smtp_pass}\n",
            f"EMAIL_FROM={email_from}\n",
            f"EMAIL_TO={email_to}\n",
        ]
        lines.extend(smtp_lines)
        ENV_FILE.write_text("".join(lines), encoding="utf-8")
        ok("Email configuration saved to .env")

        if confirm("Test email configuration now?", default=True):
            test_cmd = f"{sys.executable} \"{SERVER / 'email_service.py'}\" --test"
            r = run(test_cmd, cwd=SERVER, label="Testing SMTP connection")
            if r.returncode == 0:
                ok("Email test successful")
            else:
                warn("Email test failed — check your credentials")
        return True
    else:
        info("Skipping email configuration. Tunnel URL will be printed to console.")
        # Ensure .env exists with empty SMTP
        if not ENV_FILE.exists():
            ENV_FILE.write_text("# TouchMorph Configuration\n", encoding="utf-8")
        return True


# ─── Step 4: Log Check ─────────────────────────────────────────────────


def check_logs():
    heading("Step 4: Event Logs")
    db_path = SERVER / "touchmorph.db"
    if not db_path.exists():
        info("No logs yet (first run)")
        return True

    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        count = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
        if count > 0:
            ok(f"{count} events logged")
            if not QUIET and confirm("Show recent logs?", default=False):
                rows = conn.execute(
                    "SELECT token, event, ts FROM logs ORDER BY id DESC LIMIT 20"
                ).fetchall()
                for row in rows:
                    print(f"    [{row[2]:.0f}] {row[0][:8]}... {row[1]}")
        else:
            info("Log table is empty")
        conn.close()
    except Exception as e:
        warn(f"Could not read logs: {e}")
    return True


# ─── Main ──────────────────────────────────────────────────────────────


def main():
    print()
    print(f"{BOLD}{CYAN}  ╔══════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}  ║       TouchMorph Setup Wizard        ║{RESET}")
    print(f"{BOLD}{CYAN}  ╚══════════════════════════════════════╝{RESET}")
    print()

    steps = [
        ("Python Dependencies", check_python),
        ("Client Build", check_node),
        ("Email Registration", configure_email),
        ("Log Check", check_logs),
    ]

    for i, (name, func) in enumerate(steps, 1):
        print(f"{BOLD}Step {i}/{len(steps)}: {name}{RESET}")
        success = func()
        if not success:
            warn(f"Step {i} had issues. Continuing anyway.")
        print()

    heading("Setup Complete")
    ok("TouchMorph is ready!")

    if not QUIET and confirm("Start TouchMorph now?", default=True):
        print()
        run(f"{sys.executable} \"{SERVER / 'main.py'}\"", cwd=SERVER,
            label="Starting server ...")
    else:
        info("Run 'python start.py' to start the server.")
        info("Run 'python setup.py' again to reconfigure.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Setup cancelled{RESET}")
        sys.exit(1)
