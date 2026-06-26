# AGENTS.md — Remote Mouse v1.0.0

Instructions for LLM coding agents working on this project.

## Project Overview

Remote Mouse is a browser-based remote mouse app. The laptop runs everything (Python server + cloudflared tunnel), the phone just opens a URL — zero phone installation.

### Stack
- **Backend:** Python 3.10+, Flask, Flask-SocketIO, pyautogui
- **Frontend:** Single HTML files, vanilla JS, no build tools
- **Tunnel:** cloudflared (optional, for remote access)
- **Email:** SMTP via `smtplib` (standard library)

## Verify Before/After Changes

Always run these checks after making code changes:

```bash
# From project root
python -m py_compile src/server.py && python -m py_compile src/cli.py && python -m py_compile src/email_service.py
```

## Run the App

```bash
# With REPL control panel (recommended) — auto-opens setup wizard
python src/cli.py

# Direct server (no CLI)
python src/server.py
```

## Project Structure

```
Remote_Mouse/
  src/              Python source
    server.py         Flask server, WebSocket, REST API, pyautogui, cloudflared
    cli.py            REPL control panel, subprocess, live logs
    email_service.py  SMTP sender (importable, also CLI via --send/--test)
  frontend/         Web frontend
    index.html        Main mouse control page (touchpad, media, link)
    setup.html        Setup wizard (3 cases, email, live logs, success)
    static/
      socket.io.min.js  Socket.IO client v4.7.5 (49KB, served locally)
  scripts/          Legacy launchers (advanced users)
    start.ps1         Windows launcher
    start.sh          Linux/macOS launcher
  docs/             Reference documentation
  .env.example      SMTP config template (copy to .env)
```

## Key Conventions

- **No build step.** Frontend is vanilla HTML/CSS/JS. No npm, webpack, vite.
- **Local socket.io.** Socket.IO client is in `frontend/static/socket.io.min.js`, served locally. Never revert to CDN.
- **No authentication.** The server trusts the network.
- **eventlet is required.** `src/server.py` uses `eventlet.monkey_patch()` at line 1 and `async_mode='eventlet'`. Do not remove.
- **`static_folder=None` is required.** Flask app is created with `Flask(__name__, static_folder=None)`. Without this Flask 3.0's built-in handler intercepts `/static/` requests.
- **Static files cached 24h.** `Cache-Control: public, max-age=86400` on static files. `index.html` and `setup.html` use `no-cache, must-revalidate`.
- **socket.io script at end of body.** Not in `<head>`. Page renders before 49KB library downloads.
- **Favicon route exists.** `/favicon.ico` returns 204 No Content.
- **WebSocket-first client.** `transports: ['websocket', 'polling']` with 5s fallback.
- **pyautogui tuning:** Always `FAILSAFE = False` and `PAUSE = 0`.
- **Logging:** All events go to stdout and `events.log` at project root.
- **Thread safety:** CLI launches server as a subprocess (`subprocess.Popen`). Do not change to threading.
- **Setup flow:** `cli.py` starts server, auto-opens browser to `/setup`. Setup wizard offers 3 connection cases. Remote case triggers cloudflared + email.
- **`events.log` and `.tunnel_url`** are created at project root and gitignored.

## Common Mistakes to Avoid

- Do NOT add QR code generation — explicitly removed per user request
- Do NOT add CDN links for socket.io — must be served locally
- Do NOT change file paths without updating all references (PROJECT_ROOT, FRONTEND_DIR)
- Do NOT remove the `PROJECT_ROOT = os.path.dirname(...)` setup at top of src/*.py — all paths derive from it
- Do NOT add authentication layers without explicit user request
- Do NOT add npm/node/build tooling
- Do NOT change the subprocess approach in cli.py (Flask-SocketIO has threading issues)
