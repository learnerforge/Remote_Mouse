# Remote Mouse

Turn your phone into a wireless mouse and media remote for your laptop. **Zero installation on the phone** — just open a URL in the browser.

## Overview

Remote Mouse is a client-server application that lets you control your laptop's mouse cursor and media playback from any phone or tablet with a modern browser. The laptop runs a Python server (Flask + Socket.IO) that receives touch events over a WebSocket and translates them into mouse movements, clicks, scrolls, and keyboard shortcuts using `pyautogui`.

The phone gets the connection URL either via email (SMTP configured on the laptop) or by typing it manually. A Cloudflare tunnel (cloudflared) provides secure HTTPS access from anywhere without port forwarding.

## How It Works

```
Phone Browser                 Cloudflare Edge              Your Laptop
     |                             |                            |
     |  open URL from email        |                            |
     +-----------------------------+----------------------------+
     |                             |                            |
     |  HTTPS request              |  cloudflared tunnel        |
     | --------------------------->| -------------------------->|
     |                             |                            |
     |  index.html served locally  |                            |
     | <---------------------------| <--------------------------|
     |                             |                            |
     |  WebSocket (touch events)   |                            |
     | --------------------------->| -------------------------->|
     |                             |              pyautogui    |
     |                             |              moves mouse  |
```

## Features

| Feature | What it does |
|---------|-------------|
| **Touchpad** | Touch and drag to move cursor. Tap to click. Two-finger scroll. |
| **Left/Right Click** | Dedicated buttons at the bottom for precise clicks. |
| **Drag Mode** | Toggle to hold the left button while dragging (for selections, moving windows). |
| **Media Controls** | Play/Pause, Next/Previous track, Volume up/down/mute. |
| **Sensitivity** | Adjustable mouse speed slider (0.2x to 3.0x). |
| **Tunnel URL delivery** | Auto-emails the tunnel URL to your phone so you just tap to connect. |
| **Local fallback** | If cloudflared is not installed, use the local network IP directly. |
| **Zero phone setup** | No app store, no installation, no permissions. Just a browser. |
| **Auto-reconnect** | WebSocket reconnects automatically with exponential backoff. |
| **Live action log** | All events printed to terminal with timestamps and colorized output. |
| **REPL control panel** | `cli.py` provides an interactive terminal with status, log, and server management. |

## Project Structure

```
remote-mouse/
+-- server.py              # Flask server + Socket.IO + pyautogui
+-- email_service.py       # SMTP email sender for tunnel URL
+-- cli.py                 # REPL control panel (launches server as subprocess)
+-- index.html             # Single-page frontend (all CSS/JS embedded)
+-- requirements.txt       # Python dependencies
+-- .env.example           # SMTP configuration template
+-- .env                   # Your SMTP settings (create from .env.example)
+-- .gitignore
+-- LICENSE
+-- README.md
+-- static/
|   +-- socket.io.min.js   # Local Socket.IO client (no CDN dependency)
+-- scripts/
|   +-- start.ps1          # Windows launcher (Powershell)
|   +-- start.sh           # Linux/macOS launcher (Bash)
+-- docs/
    +-- ARCHITECTURE.md    # System architecture deep dive
    +-- SETUP.md           # Complete setup guide
    +-- USAGE.md           # Usage instructions
    +-- PROTOCOL.md        # WebSocket event protocol reference
    +-- CONFIGURATION.md   # Environment and configuration reference
    +-- TROUBLESHOOTING.md # Common issues and solutions
```

## What You Need

- **Python 3.10+** — the server and CLI are written in Python
- **cloudflared** (optional) — for remote internet access via Cloudflare tunnel
- **SMTP account** (optional) — for emailing the tunnel URL to your phone

## Quick Start

### 1. Install dependencies

Open a terminal in the project directory and install the required Python packages:

```bash
pip install -r requirements.txt
```

### 2. (Optional) Configure email

Copy the template and fill in your SMTP credentials:

```bash
cp .env.example .env
```

Edit `.env` with your SMTP settings. For Gmail, you need an App Password (not your regular password). See `docs/CONFIGURATION.md` for details.

### 3. Start the server

**Windows (double-click or command line):**

```powershell
python cli.py
```

**Windows (Powershell launcher with tunnel):**

```powershell
.\scripts\start.ps1
```

**Linux/macOS:**

```bash
./scripts/start.sh
```

**Manual (two terminals):**

Terminal 1 — start the server:
```bash
python server.py
```

Terminal 2 — start the tunnel (if cloudflared is installed):
```bash
cloudflared tunnel --url http://localhost:5000
```

### 4. Connect your phone

- If you configured SMTP: Check your phone's email or SMS — the tunnel URL is there. Tap the link.
- If running locally: Open `http://<laptop-ip>:5000` in your phone browser (both devices on same WiFi).
- If using the tunnel: Copy the `https://*.trycloudflare.com` URL shown in the terminal.

That is it. The page loads instantly (socket.io JS is served locally, not from CDN) and you can start controlling the mouse.

## Use Cases

- **Presentations** — control slides from across the room
- **Media playback** — play/pause, skip tracks, adjust volume without switching apps
- **Remote desktop** — navigate your laptop from the couch
- **Smart TV / projector** — if your laptop is plugged into a TV, use your phone as a remote
- **Accessibility** — use touch gestures instead of a physical mouse

## Keyboard Shortcuts Available

The server supports these key combinations via the WebSocket protocol (can be added to the frontend easily):

| Action | Keys |
|--------|------|
| Alt+Tab | Switch applications |
| Win+D | Show desktop |
| Win+Tab | Task view |
| Win+L | Lock screen |
| Escape | Cancel/close |
| Enter | Confirm |
| Space | Activate |

## Performance Notes

- **Latency:** On the same WiFi network, latency is typically under 10ms. Through a Cloudflare tunnel, expect 50-200ms depending on your internet connection.
- **CDN elimination:** The Socket.IO client library (socket.io.min.js, 49 KB) is served from the laptop's `/static/` directory. This avoids the 3+ minute loading time that would occur if the phone had to download it from a CDN over a metered/hotspot connection.
- **pyautogui tuning:** `FAILSAFE` is disabled and `PAUSE` is set to 0 for zero-delay mouse movement.

## Contributing

This project is designed to be minimal and self-contained. The frontend is a single HTML file with no build tools. The backend is three Python files with no database, no authentication, and no external services except cloudflared and SMTP.

If you want to add features, start by reading `docs/ARCHITECTURE.md` to understand the data flow, then look at the WebSocket protocol in `docs/PROTOCOL.md`.

## License

MIT License — see `LICENSE` for details.
