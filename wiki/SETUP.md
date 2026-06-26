# Development Setup

## Prerequisites

- Python 3.10+
- Git
- (Optional) cloudflared for remote tunnel testing
- (Optional) SMTP account for email testing

## Initial Setup

```bash
# Clone the repository
git clone https://github.com/learnerforge/Remote_Mouse.git
cd Remote_Mouse

# Install Python dependencies
pip install -r requirements.txt

# Verify compilation
python -m py_compile src/server.py
python -m py_compile src/cli.py
python -m py_compile src/email_service.py

# (Optional) Configure email
cp .env.example .env
```

## Running in Development

```bash
# With CLI (REPL + live logs)
python src/cli.py

# Direct server (for debugging with print statements)
python src/server.py
```

## Verify Changes

Always run after making code changes:

```bash
# Python compilation check
python -m py_compile src/server.py && python -m py_compile src/cli.py && python -m py_compile src/email_service.py
```

## Project Structure

```
Remote_Mouse/
  src/              Python source
    server.py         Flask + Flask-SocketIO + pyautogui + cloudflared
    cli.py            REPL control panel, subprocess manager
    email_service.py  SMTP sender (importable + CLI)
  frontend/         Web frontend
    index.html        Main mouse control page
    setup.html        3-step setup wizard
    static/
      socket.io.min.js  Socket.IO v4.7.5 (49 KB)
  docs/             User documentation (HTML)
  wiki/             Contributor documentation (Markdown)
  scripts/          Legacy launcher scripts
```

## Quick Reference

| Command | Description |
|---------|-------------|
| `pip install -r requirements.txt` | Install dependencies |
| `python src/cli.py` | Start with REPL (recommended) |
| `python src/server.py` | Start server directly |
| `python src/email_service.py --test` | Test SMTP config |
| `python -m py_compile src/*.py` | Verify syntax |
| `netsh advfirewall firewall add rule name="Remote Mouse 5000" dir=in action=allow protocol=TCP localport=5000` | Windows firewall |
