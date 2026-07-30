# Architecture — Design Decisions

This document covers the **why** behind architectural choices, from a contributor's perspective.

## Why eventlet?

Flask-SocketIO supports three async modes: `eventlet`, `gevent`, and `threading`. Only `eventlet` provides native WebSocket support. Without it, the server falls back to HTTP long-polling which adds significant latency.

```python
import eventlet
eventlet.monkey_patch()
```

**Trade-off:** eventlet v0.41.0 has known issues on some Python 3.13 builds. If upgrading Python, verify eventlet compatibility first.

## Why `static_folder=None`?

Flask 3.0 introduced a built-in static file handler that intercepts `/static/` requests before our custom route. Setting `static_folder=None` disables this so our route takes priority:

```python
app = Flask(__name__, static_folder=None)
```

**Alternative considered:** Using `send_from_directory` with a different URL prefix (e.g., `/assets/`). Rejected because it would break the existing `/static/` convention.

## Why subprocess for CLI?

Flask-SocketIO has known threading issues when combined with `socketio.run()`. Running the server as a subprocess avoids GIL contention and ensures clean process isolation:

```python
server_proc = subprocess.Popen([sys.executable, '-u', server_script], ...)
```

**Alternative considered:** `threading.Thread` — rejected due to Flask-SocketIO's documented instability with threads.

## Why pairing auth?

v1.1.0 introduced a pairing code system (6-char hex code, e.g. `A3F1B9`). At startup, the server generates a `PAIRING_CODE` displayed in the terminal. The client must send a `pair` event with this code within 60 seconds; the server responds with a session token stored in `localStorage`.

```python
PAIRING_CODE = secrets.token_hex(3).upper()  # 6 hex chars
```

**Why not password-based?** A pairing code is single-use, volatile (invalidates on restart), and requires physical proximity to the laptop. This is stronger than a static password for the "personal device" threat model.

**Flow:** Server starts → code printed → phone connects via WebSocket → sends `pair` event → validates → returns session token → all subsequent events require token via `@require_auth`.

## Why local socket.io?

The Socket.IO client library (49 KB minified) was originally loaded from CDN. On phone hotspot connections, this took 3+ minutes due to:
- DNS resolution through mobile carrier
- CDN routing over metered connection
- Lack of caching on first load

Serving it locally from `/static/` eliminates this entirely — the page loads in under 1 second.

## Why `FAILSAFE=True` and `PAUSE=0`?

```python
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0
```

- **FAILSAFE:** Re-enabled in v1.1.0 as a safety measure. The initial release (`FAILSAFE=False`) was a mistake — it disabled an emergency kill switch. With pairing auth now preventing unauthorized access, the failsafe can safely be re-enabled. If remote control goes haywire, moving the mouse to a screen corner kills the operation.
- **PAUSE:** pyautogui adds a 100ms delay between every call by default. Setting to 0 removes this for responsive cursor movement.

## Why `deque(maxlen=200)` for logs?

The in-memory log history uses a bounded deque to prevent unbounded memory growth during long sessions. The 200-entry limit keeps memory usage under ~50 KB while providing enough history for the CLI's `log` command.

## Why rate limiting?

Each authenticated session is limited to 30 calls per second per action type. The `@with_ratelimit('action_name')` decorator uses a token bucket per session-action pair:

```python
def with_ratelimit(action):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(sid, *args, **kwargs):
            if not ratelimit(sid, action, 30):
                return
            return func(sid, *args, **kwargs)
        return wrapper
```

This prevents runaway loops (e.g., a stuck touch event firing 1000 moves/sec) and limits abuse potential.

**Why not global rate limiting?** Per-session-per-action means one misbehaving client doesn't starve others, and different actions (move vs click) have independent budgets.

## Why PII redaction?

All log output passes through `PIIRedactFilter`, a logging filter that scrubs:
- Email addresses (`user@example.com` → `***@***.com`)
- URLs (`https://example.com/path` → `***`)
- IPv4/IPv6 addresses (`192.168.1.1` → `***.***.***.***`)

This ensures logs can be shared for debugging without exposing personal information. The filter is applied to both the `events.log` file handler and the stdout handler.

## Why security headers?

The Flask app sets these headers on every response:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Frame-Options` | `DENY` | Prevents clickjacking |
| `Content-Security-Policy` | `default-src 'self'` | Blocks inline scripts/XSS |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME sniffing |
| `Referrer-Policy` | `no-referrer` | Disables referrer leakage |
| `Permissions-Policy` | `camera=(), microphone=(), ...` | Disables sensor access |

CSP is intentionally restrictive — the only scripts allowed are served from `/static/`. This means any injected script is blocked by the browser itself.

## Why dynamic CORS?

Instead of the common `CORS(app, origins="*")`, v1.1.0 uses a validation function:

```python
def allowed_origin(origin):
    if not origin:
        return False
    if origin.startswith(('http://localhost', 'http://127.0.0.1')):
        return True
    if is_lan_ip(origin):
        return True
    return origin == tunnel_url
```

This ensures CORS is only granted to known-good origins: localhost, LAN IPs, and the current tunnel URL. The wildcard approach was a security gap — any website could have initiated a WebSocket connection.

## Why 30-second cloudflared timeout?

```python
deadline = 30
```

Cloudflared typically responds with a tunnel URL within 3–5 seconds. The 30-second timeout prevents the setup wizard from hanging indefinitely if cloudflared fails to start (missing binary, network restrictions, port conflict).

## Why no database?

The application has no persistent state beyond:
- `events.log` (append-only text file)
- `.tunnel_url` (single-line text file)
- `.env` (SMTP configuration)

All settings are session-only. Profile storage is planned for future versions (v1.0.4+ in the version plan).

## Frontend Conventions

### Touch Events vs Pointer Events

The frontend uses Touch Events API (`touchstart`, `touchmove`, `touchend`) rather than Pointer Events (`pointerdown`, `pointermove`, `pointerup`). This ensures broader compatibility with older mobile browsers.

**Trade-off:** Pointer Events unify mouse and touch handling. Touch Events requires separate handling for each, but avoids issues with pointer event fallback on some Android browsers.

### Socket.IO at Bottom of Body

The `<script>` tag for socket.io.min.js is placed at the end of `<body>`, not in `<head>`. This ensures the page HTML and CSS render before the 49 KB library starts downloading, eliminating render-blocking delays.

### Inline CSS/JS

All CSS and JavaScript is inlined in `index.html`. This eliminates extra HTTP requests and ensures the page works as a single file. The only external dependency is socket.io.min.js served from `/static/`.
