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

## Why no authentication?

The project is designed for personal use on trusted networks. Adding authentication would:
- Increase complexity for the 99% use case (personal LAN)
- Require session management or token storage
- Add friction to the setup wizard flow

**Safety mechanisms:** Random tunnel URLs (64-bit entropy), URL volatility (changes on restart), network segmentation.

## Why local socket.io?

The Socket.IO client library (49 KB minified) was originally loaded from CDN. On phone hotspot connections, this took 3+ minutes due to:
- DNS resolution through mobile carrier
- CDN routing over metered connection
- Lack of caching on first load

Serving it locally from `/static/` eliminates this entirely — the page loads in under 1 second.

## Why `FAILSAFE=False` and `PAUSE=0`?

```python
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0
```

- **FAILSAFE:** pyautogui's default failsafe throws an exception when the mouse reaches a screen corner. This is useful for emergencies but breaks remote control when the user moves the cursor quickly.
- **PAUSE:** pyautogui adds a 100ms delay between every call by default. Setting to 0 removes this for responsive cursor movement.

## Why `deque(maxlen=200)` for logs?

The in-memory log history uses a bounded deque to prevent unbounded memory growth during long sessions. The 200-entry limit keeps memory usage under ~50 KB while providing enough history for the CLI's `log` command.

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
