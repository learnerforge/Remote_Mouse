# Architecture

This document describes the system architecture of Remote Mouse — how the components fit together, the data flow, and the design decisions behind each piece.

## System Overview

Remote Mouse follows a simple client-server architecture. The server runs on the laptop and serves a web page to the phone. The phone (client) connects over WebSocket and sends touch events. The server translates those events into OS-level mouse and keyboard actions using `pyautogui`.

There is no database, no persistent storage (beyond a log file), and no authentication layer. The design prioritizes simplicity, zero phone installation, and minimal latency.

## Component Diagram

```
+---------------------+       WebSocket        +---------------------+
|   Phone Browser     | <====================> |   Python Server     |
|   (index.html)      |    socket.io events    |   (server.py)       |
|                     |                        |                     |
|  +---------------+  |   mouse_move, click,   |  +---------------+  |
|  | Touch Events  |  |   scroll, media, key   |  | pyautogui     |  |
|  | API           |  | ---------------------> |  | (OS control)  |  |
|  +---------------+  |                        |  +---------------+  |
|         |           |                        |                     |
|  +---------------+  |   screen_info,         |  +---------------+  |
|  | Socket.IO     |  |   tunnel_url           |  | Flask-SocketIO|  |
|  | Client (local)|  | <--------------------- |  | (WebSocket)   |  |
|  +---------------+  |                        |  +---------------+  |
|         |           |                        |         |           |
|  +---------------+  |   HTTP (initial load)  |  +---------------+  |
|  | Browser       |  | <--------------------- |  | Flask (HTTP)  |  |
|  | (HTML/CSS/JS) |  |   GET /, /static/*     |  | (file serve)  |  |
|  +---------------+  |                        |  +---------------+  |
+---------------------+                        +---------------------+
                                                        |
                                               +---------------------+
                                               | cloudflared tunnel  |
                                               | (optional)          |
                                               | localhost:5000 -->  |
                                               | *.trycloudflare.com |
                                               +---------------------+
```

## Component Breakdown

### 1. Frontend (`index.html`)

A single HTML file that contains all the user interface markup, CSS styles, and client-side JavaScript. There are no external dependencies loaded at runtime except the Socket.IO client library, which is served locally.

**Key sections:**

- **Status bar** — shows connection state (green dot when connected, gray when disconnected) and the laptop's local IP address.
- **Touchpad** — captures touch events (touchstart, touchmove, touchend, touchcancel) and translates them into mouse movements, clicks, and scroll actions.
- **Click bar** — provides dedicated Left Click and Right Click buttons, plus a Drag Mode toggle.
- **Media page** — provides Play/Pause, Next, Previous, Volume Up, Volume Down, and Mute buttons.
- **Link page** — displays the tunnel URL with a copy-to-clipboard button and an email request form. The form sends the URL via the server's `/api/send-url` endpoint.
- **Bottom navigation** — switches between Touchpad, Media, and Link pages. Also opens the Sensitivity settings panel.
- **Sensitivity panel** — a slide-up panel with a range slider (0.2x to 3.0x) that adjusts the mouse speed multiplier.

**Design decisions:**

- **No build step.** The file is served as-is. No webpack, no vite, no npm install on the laptop.
- **Local socket.io.** The Socket.IO client (49 KB minified) is downloaded once into `static/socket.io.min.js` and served from the laptop. This eliminates the 3+ minute CDN loading time on phone hotspot connections.
- **Touch Events API** is used instead of Pointer Events for broader mobile browser compatibility.
- **Haptic feedback** via `navigator.vibrate(10)` on clicks and button presses.

### 2. Server (`server.py`)

A Python application built on Flask and Flask-SocketIO. It serves the frontend files, manages WebSocket connections, and executes system commands via pyautogui.

**Key responsibilities:**

- Serve `index.html` at `GET /`
- Serve static files from the `static/` directory at `/static/<path>`
- Provide REST API endpoints (`/api/tunnel-url`, `/api/send-url`)
- Accept WebSocket connections and process events
- Execute mouse movements, clicks, scrolls, media keys, and keyboard shortcuts via pyautogui
- Log all actions with timestamps to both stdout and `events.log`

**WebSocket event handlers:**

| Event | Handler | Action |
|-------|---------|--------|
| `connect` | `handle_connect` | Send screen dimensions and connection info |
| `disconnect` | `handle_disconnect` | Log disconnection |
| `mouse_move` | `handle_move` | Move cursor by delta using `moveRel()` |
| `mouse_down` | `handle_down` | Press mouse button |
| `mouse_up` | `handle_up` | Release mouse button |
| `click` | `handle_click` | Single click |
| `double_click` | `handle_double_click` | Double click |
| `scroll` | `handle_scroll` | Scroll by delta |
| `media` | `handle_media` | Media keys (play/pause, next, prev, volume, mute) |
| `key` | `handle_key` | Keyboard shortcuts (alt+tab, win+d, etc.) |
| `request_tunnel_url` | `handle_request_tunnel_url` | Send current tunnel URL to client |

**Design decisions:**

- **Flask-SocketIO** handles both HTTP and WebSocket in a single process. No separate WebSocket server needed.
- **pyautogui.FAILSAFE = False** — disables the failsafe that would crash on corner movements.
- **pyautogui.PAUSE = 0** — removes the built-in 100ms pause between pyautogui calls for responsive control.
- **Logging** uses a `deque(maxlen=200)` for in-memory history plus a persistent file. The file is read by `cli.py` for the `log` command.

### 3. CLI Control Panel (`cli.py`)

An interactive REPL that launches the server as a subprocess and displays its log output in real time with colorized formatting.

**Features:**

- Launches `server.py` as a child process with unbuffered output (`-u` flag)
- Captures stdout in a background thread and prints it with color coding
- Provides commands: `status`, `log`, `clear`, `help`, `exit`
- Cleans up the server process on exit

**Design decisions:**

- **Subprocess approach** avoids GIL and threading issues with Flask-SocketIO. The server runs in its own process and the CLI simply reads its output.
- **Colorama** is used for cross-platform colored terminal output.
- The server's stdout is piped directly to the CLI's display — no separate log parsing needed.

### 4. Email Service (`email_service.py`)

A standalone module for sending email via SMTP. It is imported by `server.py` and can also be run from the command line.

**Capabilities:**

- Reads configuration from `.env` file or environment variables
- Supports SMTP with STARTTLS (port 587) and SSL (port 465)
- Retries failed sends up to 3 times with exponential backoff
- Builds a clean HTML email with the tunnel URL as a tappable link
- CLI mode: `python email_service.py --send <url>` or `--test`

**Design decisions:**

- **Importable by server.py** — the `api_send_url` route calls `send_email()` directly with the tunnel URL.
- **Standalone CLI** — useful for testing SMTP configuration without starting the full server.
- **No external email API** — uses only Python standard library (`smtplib`, `ssl`) plus `MIMEText`/`MIMEMultipart`.

### 5. Cloudflare Tunnel (cloudflared)

An external binary that creates a secure tunnel from Cloudflare's edge network to `localhost:5000`. This provides:

- A public HTTPS URL that works on any network
- Built-in DDoS protection and edge caching
- No port forwarding, no static IP, no DNS configuration

The tunnel URL is written to `.tunnel_url` by the startup scripts and read by the server to expose it via the API and WebSocket.

## Data Flow

### Connection Flow

1. **Server starts** — `server.py` binds to `0.0.0.0:5000`
2. **Tunnel starts** (optional) — `cloudflared tunnel --url http://localhost:5000` creates an HTTPS tunnel; the URL is written to `.tunnel_url`
3. **User gets URL** — either via email (SMTP), scanning terminal output, or local network IP
4. **Phone opens URL** — browser loads `index.html` from the server
5. **WebSocket connects** — `index.html` creates a Socket.IO connection back to the server
6. **Server confirms** — `handle_connect` sends screen dimensions and URLs
7. **User interacts** — touch and button events flow over WebSocket

### Event Flow

```
Touch on phone screen
  -> touchstart event in browser
  -> touchmove events with delta coordinates
  -> socket.emit('mouse_move', { dx, dy })
  -> server.handle_move()
  -> pyautogui.moveRel(dx, dy)
  -> log_msg("> move (+0012, -0005)")
  -> printed to stdout and events.log
```

## Logging Architecture

```
server.py            cli.py
   |                    |
   | stdout (pipe) ----> reader thread --> terminal display
   |                    |
   | events.log (file)  | reader thread -> events.log (same file)
   |                    |
   | (also)            cmd_log() -> reads events.log -> terminal display
```

The server writes to stdout and `events.log`. The CLI captures stdout via a pipe for real-time display. The `log` command in the REPL reads `events.log` directly to show recent history.

## Security Model

Remote Mouse has **no authentication**. The security relies on:

1. **Network segmentation** — the server binds to `0.0.0.0:5000`, so it is accessible to anyone on the local network.
2. **URL randomness** — the Cloudflare tunnel URL is randomly generated (64-bit entropy) and hard to guess.
3. **URL volatility** — the tunnel URL is valid only while the tunnel process runs. Stopping cloudflared invalidates the URL.
4. **Trust model** — designed for personal use on trusted networks. Do not expose to untrusted users.

For additional security, consider:
- Running behind a reverse proxy with basic auth
- Using a firewall to restrict access to specific IP addresses
- Adding authentication to the Flask routes
