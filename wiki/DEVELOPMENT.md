# Development Workflow

## Branch Strategy

- `main` — stable, released versions
- Feature branches for individual specs from the version plan

## Coding Conventions

### Python

- Use `log_ok()`, `log_info()`, `log_warn()` instead of `print()` for server events (PII auto-redacted)
- Import `eventlet` monkey patch at line 1 of `server.py`
- All paths derive from `PROJECT_ROOT` — never use relative paths
- `pyautogui.FAILSAFE = True` and `PAUSE = 0` at module level
- All socket handlers must have `@with_ratelimit('action_name')` decorator
- New socket handlers must be added to `ALLOWED_ACTIONS` set
- Never add handlers that bypass `require_auth()` — always decorate with `@require_auth`
- Never log raw IPs, emails, or URLs directly — use the logging helpers
- Log output goes to `.remote_mouse_logs/events.log` (auto-created)

### JavaScript

- Vanilla JS only — no frameworks, no build tools
- Use `touchstart`/`touchmove`/`touchend` events, not Pointer Events
- Socket.IO at end of `<body>`, not in `<head>`
- Inline all CSS and JS in `index.html`

### HTML/CSS

- Dark theme (`#0a0a0a` background)
- Accent color: `#4ade80` (green)
- Error/danger: `#f87171` (red)
- Responsive: works on phone screens (320px+ width)
- No external fonts — use system font stack

## Testing

Manual testing checklist:

1. **HTTP routes:** `GET /`, `/setup`, `/static/*`, `/favicon.ico`, `/api/*`
2. **WebSocket:** Connect, move, click, scroll, media, disconnect
3. **Setup wizard:** All 3 cases (localhost, same-wifi, remote)
4. **CLI:** Start, stop, `status`, `log` commands
5. **Email:** `python src/email_service.py --test`
6. **Windows Firewall:** Port 5000 accessible from LAN
7. **Phone browser:** Chrome (Android), Safari (iOS)

Compilation check:

```bash
python -m py_compile src/server.py && python -m py_compile src/cli.py && python -m py_compile src/email_service.py
```

## Pull Request Guidelines

1. One version/spec per PR (follow version_control.md ordering)
2. Update both `docs/` (HTML) and `wiki/` (Markdown) if adding features
3. Include compilation check in PR description
4. Test on at least one phone browser before submitting

## Common Pitfalls

| Pitfall | Why | Prevention |
|---------|-----|------------|
| Forgetting `eventlet.monkey_patch()` | WebSocket won't work | Keep it at line 1 of server.py |
| Using CDN for socket.io | 3-minute load on hotspot | Serve from `/static/socket.io.min.js` |
| Changing file paths | Breaks PROJECT_ROOT derivation | Update all references in all files |
| Forgetting `@require_auth` on new handlers | Unauthenticated mouse access | Always add the decorator |
| Forgetting `@with_ratelimit` on new handlers | No rate limiting on the action | Always add the decorator |
| Logging raw IPs/emails | PII leak in logs | Use the logging helpers |
| Forgetting to add new actions to `ALLOWED_ACTIONS` | Handler silently ignored | Add to set at module top |
| Removing `static_folder=None` | Flask 3.0 intercepts /static | Keep it in Flask constructor |
| Using threads for CLI | Flask-SocketIO threading issues | Use subprocess.Popen |
