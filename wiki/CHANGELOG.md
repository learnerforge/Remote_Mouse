# Changelog

All notable changes to Remote Mouse are documented here.

---

## v1.1.1 — Security Hardening

**Date:** 2026-07-31

### Fixed
- Removed unauthenticated `GET /api/pairing-code` endpoint — the pairing code now lives only on the laptop screen (this endpoint let anyone on the LAN fetch the code and defeat pairing)
- Restored CSP directives (`script-src 'unsafe-inline'`, `connect-src ws://* wss://*`, `img-src 'self' data:`) that were breaking inline scripts and WebSocket connections
- `screen_info` (tunnel URL, LAN IP, screen dims) now emitted only to authenticated clients
- Email endpoint hardening: `POST /api/send-url` now requires the pairing token and is IP-rate-limited (was an open SMTP relay)
- Pairing brute-force protection: `pair` event is rate-limited and 5 failed attempts trigger a 60s lockout
- Removed dead `PAIRING_EXPIRY` constant
- Fixed `tests/test_email_service.py` setup (temp file was named `.env` inside a temp dir, not at `tempdir/.env`)

### Changed
- `pairing:submit` event renamed to `pair` (matching implementation); docs updated
- Corrected CHANGELOG pin note below (`flask-socketio>=5.6.0` — `>=5.14.0` does not exist on PyPI)

---

## v1.1.0 — Security Release

**Date:** 2026-07-30

### Added
- Mandatory pairing authentication (6-char code shown on laptop, entered on phone)
- Dynamic CORS origin validation (replaced wildcard `*`)
- Rate limiting (30 calls/sec per action per session)
- Action allowlist (10 approved socket events)
- OS key combo blocklist (Ctrl+Alt+Del, Win+L, etc.)
- PII redaction filter for all logs
- Security headers (X-Frame-Options, CSP, X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
- Static file extension whitelist (only .js/.css/.png/.ico/.svg/.json/.map)
- Weekly pip-audit CI workflow
- Subprocess hardening (shutil.which, stdin=DEVNULL)
- WebSocket buffer size limit (64 KB)
- `GET /api/pairing-code` endpoint (removed in v1.1.1 — security hole)

### Changed
- `pyautogui.FAILSAFE` re-enabled (`False` → `True`)
- Logs moved to `.remote_mouse_logs/events.log` with 0o700 permissions
- Dependencies pinned to secure minimum versions (eventlet>=0.40.3, flask-socketio>=5.6.0)

---

## v1.0.0 — DPI Presets

**Date:** 2026-06-26

### Added
- DPI preset buttons (400/800/1600/3200) in the click bar
- DPI-to-sensitivity conversion on the server
- Effective DPI label next to the sensitivity slider

### Changed
- Sensitivity slider now shows equivalent DPI value
- Default sensitivity maps to 800 DPI

---

## v5.0.1 — Bugfix Release

**Date:** 2026-06-25

### Fixed
- Two-finger scroll not working (`prev1.y` → `prev1.lastY`)
- Stale cursor position after mixed 1→2→1 finger sequences

### Changed
- Project restructured into `src/` and `frontend/` folders
- All paths derived from `PROJECT_ROOT` constant
- Removed orphan code across all 5 source files

### Removed
- `log_history` deque and `log_error()` from server.py
- Orphan socket handlers (`mouse_down`, `mouse_up`, `double_click`, `key`)
- Redundant path traversal check
- Orphan CSS and JS variables from frontend
- `import tempfile` and `log_tmp` alias from cli.py

---

## v5.0.0 — Initial Release

**Date:** 2026-06-20

### Added
- Flask + Flask-SocketIO server with eventlet async mode
- pyautogui mouse control (move, click, scroll)
- Media key support (play/pause, next/prev, volume)
- WebSocket-based touchpad with sensitivity slider
- Left/right click bar with drag mode toggle
- Cloudflare tunnel integration with auto-detection
- SMTP email delivery for tunnel URL
- 3-step setup wizard at `/setup`
- REPL control panel with live colorized logs
- Local socket.io serving (no CDN dependency)
- Windows Firewall rule management
- Cross-platform startup scripts (PowerShell + Bash)
