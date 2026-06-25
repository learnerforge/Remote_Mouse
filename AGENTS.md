# AGENTS.md — Remote Mouse

Instructions for LLM coding agents working on this project.

## Project Overview

Remote Mouse is a browser-based remote mouse app. The laptop runs everything (Python server + cloudflared tunnel), the phone just opens a URL — zero phone installation.

### Stack
- **Backend:** Python 3.10+, Flask, Flask-SocketIO, pyautogui
- **Frontend:** Single HTML file, vanilla JS, no build tools
- **Tunnel:** cloudflared (optional, for remote access)
- **Email:** SMTP via `smtplib` (standard library)

## Verify Before/After Changes

Always run these checks after making code changes:

```bash
# Syntax check all Python files
python -m py_compile server.py && python -m py_compile cli.py && python -m py_compile email_service.py
```

## Run the App

```bash
# With REPL control panel (recommended)
python cli.py

# Direct server (no CLI)
python server.py
```

## Key Conventions

- **No build step.** The frontend is a single `index.html` with embedded CSS/JS. No npm, webpack, vite.
- **Local socket.io.** The Socket.IO client (`static/socket.io.min.js`, 49 KB) is served locally, not from CDN. Never revert to CDN — it causes 3+ minute load times on phone hotspot connections.
- **No authentication.** The server trusts the network. Anyone with the URL can control the mouse.
- **eventlet is required.** `server.py` uses `eventlet.monkey_patch()` at line 1 and `async_mode='eventlet'` for native WebSocket support. Do not remove eventlet or change the async mode — without it the server falls back to HTTP long-polling only, causing 5-minute load times.
- **WebSocket-first client.** `index.html` sets `transports: ['websocket', 'polling']` — tries WebSocket instantly, falls back to HTTP long-polling only if WebSocket fails. The polling fallback is instant (same HTTP server that served the page) and the 5s timeout on `io()` guarantees fast fallback.
- **pyautogui tuning:** Always keep `FAILSAFE = False` and `PAUSE = 0` in `server.py` for zero-latency control.
- **Logging:** All events go to stdout and `events.log`. The CLI reads stdout via subprocess pipe.
- **Thread safety:** CLI launches server as a subprocess (`subprocess.Popen`), not a thread. Do not change this to threading.

## Important Files

| File | Purpose |
|------|---------|
| `server.py` | Flask server, WebSocket handlers, REST API, pyautogui control |
| `cli.py` | REPL control panel, subprocess management, live log display |
| `index.html` | Single-page frontend (touchpad, media controls, link page) |
| `email_service.py` | SMTP email sender (importable by server.py, also runnable as CLI) |
| `static/socket.io.min.js` | Local Socket.IO client library |
| `.env` | SMTP credentials (gitignored) |

## Common Mistakes to Avoid

- Do NOT add QR code generation — it was explicitly removed per user request
- Do NOT add CDN links for socket.io — must be served locally
- Do NOT add authentication layers without explicit user request
- Do NOT add npm/node/build tooling — the project is intentionally build-free
- Do NOT change the subprocess approach in cli.py (Flask-SocketIO has threading issues)

## Rules

- After editing Python files, always run the syntax check command above
- After editing HTML/JS, manually verify the page loads in a browser
- Do NOT introduce new dependencies without checking with the user first
- Keep changes minimal and focused
