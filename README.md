# Remote Mouse

Turn your phone into a wireless mouse and media remote for your laptop. **Zero installation on the phone** — just open a URL in the browser.

## How It Works

Your laptop runs a small Python server and a Cloudflare tunnel. The phone connects via the tunnel URL and sends touch/click events over a WebSocket. The server translates these into actual mouse movements and keystrokes on the laptop using `pyautogui`.

```
Phone Browser                 Cloudflare Edge              Your Laptop
     │                             │                            │
     │  open URL from email        │                            │
     ├─────────────────────────────┼────────────────────────────┤
     │                             │                            │
     │  HTTPS request              │  cloudflared tunnel        │
     │ ───────────────────────────>│ ──────────────────────────>│
     │                             │                            │
     │  index.html served          │                            │
     │ <───────────────────────────│ <──────────────────────────│
     │                             │                            │
     │  WebSocket (touch events)   │                            │
     │ ───────────────────────────>│ ──────────────────────────>│
     │                             │              pyautogui     │
     │                             │              moves mouse   │
```

## Features

| Feature | What it does |
|---------|-------------|
| **Touchpad** | Touch & drag to move cursor. Tap to click. Two-finger scroll. |
| **Left/Right Click** | Dedicated buttons at the bottom. |
| **Drag Mode** | Toggle to hold the left button while dragging (for selections, moving windows). |
| **Media Controls** | Play/Pause, Next/Prev track, Volume up/down/mute. |
| **Sensitivity** | Adjustable mouse speed (0.2x – 3.0x). |
| **Tunnel URL delivery** | Auto-emails the tunnel URL to your phone so you just tap to connect. |
| **Local fallback** | If cloudflared isn't installed, use the local network IP directly. |
| **Zero phone setup** | No app store, no installation, no permissions. Just a browser. |

## Project Structure

```
remote-mouse/
├── server.py              # Flask server + Socket.IO + pyautogui
├── email_service.py       # SMTP email sender for tunnel URL
├── index.html             # Single-page frontend (all JS/CSS embedded)
├── requirements.txt       # Python dependencies
├── .env.example           # SMTP configuration template
├── .env                   # Your SMTP settings (create from .env.example)
├── .gitignore
├── LICENSE
├── README.md
└── scripts/
    ├── start.ps1          # Windows launcher
    └── start.sh           # Linux/macOS launcher
```

## Prerequisites

- **Python 3.10+** — [Download](https://www.python.org/downloads/)
- **cloudflared** (optional, for internet access) — [Download](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)
- **SMTP account** (optional, for email delivery) — Gmail, Outlook, or any SMTP provider

## Quick Start

### 1. Clone and install

```bash
git clone <repo-url> remote-mouse
cd remote-mouse
pip install -r requirements.txt
```

### 2. Configure email (optional)

Copy `.env.example` to `.env` and fill in your SMTP settings:

```bash
cp .env.example .env
```

Edit `.env`:

```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your.email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your.email@gmail.com
SMTP_TO_EMAIL=your-phone-number@vtext.com
```

> **Gmail:** Use an [App Password](https://support.google.com/accounts/answer/185833) (not your regular password).
>
> **SMS gateway:** Send to `number@vtext.com` (Verizon), `number@tmomail.net` (T-Mobile), `number@att.txt` (AT&T), or just a regular email address you check on your phone.

### 3. Start the server

**Windows:**
```powershell
.\scripts\start.ps1
```

**Linux/macOS:**
```bash
./scripts/start.sh
```

Or manually:

```bash
# Terminal 1: Start the server
python server.py

# Terminal 2: Start the tunnel (if cloudflared is installed)
cloudflared tunnel --url http://localhost:5000
```

### 4. Connect your phone

- If you configured SMTP: Check your phone's email/SMS — the tunnel URL is there.
- If running locally: Open `http://<laptop-ip>:5000` in your phone browser.
- If using the tunnel: Open the `https://*.trycloudflare.com` URL shown in the terminal.

That's it. The page loads and you can start controlling the mouse immediately.

## Manual Setup (no email)

If you don't want to configure SMTP, just start the server:

```bash
python server.py
```

The terminal prints the local IP and tunnel URL (if cloudflared is installed). Type the URL into your phone's browser manually.

## Usage

### Touchpad
| Gesture | Action |
|---------|--------|
| Single finger drag | Move cursor |
| Single finger tap | Left click |
| Two finger drag | Scroll |
| Left Click button | Left click |
| Right Click button | Right click |
| Drag toggle + drag | Hold left button + move (drag) |

### Media Controls
| Button | Action |
|--------|--------|
| ▶ | Play / Pause |
| ⏮ | Previous track |
| ⏭ | Next track |
| 🔊 Volume up | Increase volume |
| 🔉 Volume down | Decrease volume |
| 🔇 Mute | Toggle mute |

### Sensitivity
Tap the gear icon (⚙) in the bottom nav to open the sensitivity slider. Adjust from 0.2x to 3.0x.

## Architecture Details

### Server (`server.py`)
- **Flask** serves `index.html` at `GET /`.
- **Flask-SocketIO** manages WebSocket connections.
- **pyautogui** translates WebSocket events into OS mouse/keyboard actions.
- The server is stateless — no database, no authentication. Connect and control.

### Client (`index.html`)
- Single HTML file with embedded CSS and JavaScript.
- Uses the **Socket.IO client library** from CDN for WebSocket communication.
- Captures touch events using the **Touch Events API**.
- Haptic feedback via **Navigator.vibrate()** on clicks.
- Works on any modern mobile browser (Chrome, Safari, Firefox).

### Email Service (`email_service.py`)
- Reads SMTP configuration from `.env` or environment variables.
- Supports SSL (port 465) and STARTTLS (port 587).
- Sends a clean HTML email with the tunnel URL as a tappable link.
- Retries 3 times with exponential backoff on failure.

### Tunnel (`cloudflared`)
- Creates a secure HTTPS tunnel from Cloudflare's edge to `localhost:5000`.
- No port forwarding, no static IP, no DNS configuration needed.
- The URL is random and temporary — it stops when the tunnel closes.

## Security Notes

- The server has **no authentication**. Anyone on your network (or with the tunnel URL) can control your mouse.
- The tunnel URL is **random** (64-bit entropy) and **temporary** (only valid while the tunnel runs).
- For local-only use, don't install cloudflared and only use the local IP.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `cloudflared not found` | Install from [cloudflare.com](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) or use local network only. |
| Server won't start | Check port 5000 isn't in use. Change the port in `server.py`. |
| Phone can't connect locally | Ensure both devices are on the same WiFi network. Check firewall. |
| WebSocket won't connect | Cloudflare tunnels support WebSocket — ensure you're using the latest `cloudflared`. |
| Email not sending | Test with `python email_service.py --test`. Check SMTP credentials. Gmail requires an App Password. |
| Mouse movement feels off | Adjust sensitivity (⚙ icon). Try different sensitivity values. |
| `pyautogui` not clicking | On macOS, grant Accessibility permissions to Terminal/Python. |
| Port 5000 already in use | Edit the port in `server.py` or kill the other process. |

## License

MIT
