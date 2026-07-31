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
- **Pairing auth required.** A 6-char hex code is generated at startup and shown in the laptop terminal. Clients must submit it via the `pair` socket event before any mouse event is processed. Token stored in `localStorage`.
- **eventlet is required.** `src/server.py` uses `eventlet.monkey_patch()` at line 1 and `async_mode='eventlet'`. Do not remove.
- **`static_folder=None` is required.** Flask app is created with `Flask(__name__, static_folder=None)`. Without this Flask 3.0's built-in handler intercepts `/static/` requests.
- **Static files cached 24h.** `Cache-Control: public, max-age=86400` on static files. `index.html` and `setup.html` use `no-cache, must-revalidate`.
- **socket.io script at end of body.** Not in `<head>`. Page renders before 49KB library downloads.
- **Favicon route exists.** `/favicon.ico` returns 204 No Content.
- **WebSocket-first client.** `transports: ['websocket', 'polling']` with 5s fallback.
- **pyautogui tuning:** Always `FAILSAFE = True` (re-enabled for safety) and `PAUSE = 0`.
- **Logging:** All events go to stdout and `.remote_mouse_logs/events.log` at project root.
- **Thread safety:** CLI launches server as a subprocess (`subprocess.Popen`). Do not change to threading.
- **Setup flow:** `cli.py` starts server, auto-opens browser to `/setup`. Setup wizard offers 3 connection cases. Remote case triggers cloudflared + email.
- **`events.log`** (in `.remote_mouse_logs/`) and **`.tunnel_url`** are created at project root and gitignored.
- **CORS origin validation:** `cors_allowed_origins=allowed_origin` dynamically validates Origin headers against localhost, LAN IP, and tunnel URL.
- **Rate limiting:** All socket handlers use `@with_ratelimit` decorator. `RateLimiter` enforces 30 calls/sec per action per session.
- **Action allowlist:** `ALLOWED_ACTIONS` set on server; unknown socket events are silently dropped.
- **Key blocklist:** `BLOCKED_KEYS` tuple blocks dangerous combos (Ctrl+Alt+Del, Win+L, etc.).
- **Security headers:** `@app.after_request` adds X-Frame-Options, CSP, X-Content-Type-Options, Referrer-Policy, Permissions-Policy.
- **Static file whitelist:** `ALLOWED_STATIC_EXTS` tuple; unlisted extensions return 404.
- **PII redaction:** `PIIRedactFilter` logging filter redacts emails, URLs, non-loopback IPs from log output.
- **Buffer size limit:** `max_http_buffer_size=65536` on SocketIO init.
- **No pairing-code API.** There is NO REST endpoint that returns the pairing code — it is shown on the laptop screen only. Never add one back.
- **Pair attempt lockout:** 5 failed `pair` attempts per session → 60s lockout, plus `@with_ratelimit('pair')`.
- **`screen_info` is authenticated-only.** Tunnel URL / LAN IP / screen dims are emitted only after a valid token connect.
- **`/api/send-url` requires pairing token** (`X-Pairing-Token` header or JSON body) + rate limit. `/api/setup-start` is IP-rate-limited.

## Common Mistakes to Avoid

- Do NOT add QR code generation — explicitly removed per user request
- Do NOT add CDN links for socket.io — must be served locally
- Do NOT change file paths without updating all references (PROJECT_ROOT, FRONTEND_DIR)
- Do NOT remove the `PROJECT_ROOT = os.path.dirname(...)` setup at top of src/*.py — all paths derive from it
- Do NOT add authentication layers without explicit user request
- Do NOT add npm/node/build tooling
- Do NOT change the subprocess approach in cli.py (Flask-SocketIO has threading issues)
- Do NOT remove or skip the `@with_ratelimit` decorator on socket handlers — rate limiting is mandatory
- Do NOT hardcode CORS origins — use the `allowed_origin` function for dynamic validation
- Do NOT log raw socket data without PII redaction — use `PIIRedactFilter` or the `redact_pii()` helper
- Do NOT bypass pairing code verification — all socket events must check `verify_pairing(sid)` first
- Do NOT add new socket event handlers without adding the action name to `ALLOWED_ACTIONS`

## Security Conventions

### Pairing Code Flow
1. `server.py` generates `PAIRING_CODE = secrets.token_hex(3)` at module level.
2. Printed to stdout/stderr at startup and shown in the CLI/terminal. NOT exposed via any REST endpoint.
3. The phone user types the 6-char code into the pairing overlay → `pair` socket event.
4. Server returns a 32-byte `token` via `paired` event and stores `paired_sessions[sid] = {'token': ...}`.
5. Client stores the token in `localStorage`, reconnects with `auth: { token }`.
6. `handle_connect(auth)` validates the token against `paired_sessions` (rejects unknown tokens with `unauthorized`).
7. `require_auth()` guards every mouse/keyboard handler — returns `True`/`False`; unauthenticated handlers no-op.
8. Failed `pair` attempts are tracked per session; 5 failures in 60s triggers a lockout.
9. Frontend pairing overlay (inline in `index.html`) handles the entire flow.

### Rate Limiter (`RateLimiter` class)
- Per-action, per-session bucket with `max_calls=30, window=1.0`.
- `@with_ratelimit` decorator wraps socket handlers, passes sid as first arg.
- Exceeded calls silently dropped (no emit back to client).
- REST endpoints are IP-rate-limited: `rest_limiter` (5/min for `/api/send-url`) and `setup_limiter` (2/min for `/api/setup-start`).

### CORS (`allowed_origin` function)
- Accepts `http://localhost:<any port>`, `http://127.0.0.1:<any port>`.
- Accepts `http://<LAN_IP>:<any port>` (auto-detected once at startup).
- Accepts the active tunnel URL (if cloudflared is running).
- Everything else → 403 with `Origin not allowed`.

### Log Redaction (`PIIRedactFilter`)
- Regex patterns for: email addresses, URLs, IPv4 addresses (excluding 127.0.0.1).
- Redacted text replaced with `[REDACTED]`.
- Attached to both file handler (`.remote_mouse_logs/events.log`) and stdout handler.

### Key Blocklist (`BLOCKED_KEYS`)
- Blocked combos: `ctrl+alt+del`, `win+l`, `ctrl+shift+esc`, `alt+f4`, `alt+tab`, `win+d`, `ctrl+alt+tab`.
- Checked in `handle_key` socket handler before pyautogui call.
- Blocked combos are logged as warnings.

### Security Headers
Applied in `@app.after_request`:
```
X-Frame-Options: DENY
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; connect-src 'self' ws://* wss://*; img-src 'self' data:; frame-ancestors 'none'
X-Content-Type-Options: nosniff
Referrer-Policy: no-referrer
Permissions-Policy: geolocation=(), microphone=(), camera=()
```
