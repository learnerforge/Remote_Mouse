# Remote Mouse

Turn your phone into a wireless mouse and media remote for your laptop. Zero installation on the phone — just open a URL in the browser.

---

## Features

- **Touchpad** — touch and drag to move cursor, tap to click, two-finger scroll
- **Click Bar** — dedicated left, right, and DPI preset (400/800/1600/3200) buttons
- **Media Remote** — play/pause, next/previous track, volume up/down, mute
- **Sensitivity Control** — adjustable cursor speed slider (0.2x to 3.0x)
- **Drag Mode** — hold left button while dragging for selections and window movement
- **Setup Wizard** — 3-step connection guide at `/setup` with live log output
- **Tunnel URL Delivery** — auto-emails the Cloudflare tunnel URL to your phone
- **Auto-Reconnect** — WebSocket reconnects with exponential backoff (1s to 5s)
- **REPL Control Panel** — interactive terminal with status, log, and server management
- **Local Fallback** — works over same WiFi if cloudflared is not installed

---

## Tech Stack

- Language: Python 3.10+, JavaScript (vanilla)
- Framework: Flask, Flask-SocketIO
- Database: None (file-based event logging)
- Other Tools: cloudflared, pyautogui, eventlet, colorama, smtplib

---

## Installation

```bash
# Clone the repository
git clone https://github.com/learnerforge/Remote_Mouse.git

# Go to project folder
cd Remote_Mouse

# Install dependencies
pip install -r requirements.txt

# (Optional) Configure SMTP email
cp .env.example .env
```

---

## Usage

```bash
# Start with REPL control panel (recommended)
python src/cli.py

# Or start the server directly
python src/server.py
```

Open the setup wizard at `http://localhost:5000/setup` on your laptop to pick your connection type. Then open the provided URL on your phone — the page loads instantly and you can start controlling the mouse.

---

## Project Structure

```
Remote_Mouse/
│── src/                 # Python source (server, cli, email_service)
│── frontend/            # Web frontend (index.html, setup.html, static/)
│── docs/                # User documentation (HTML pages)
│── wiki/                # Contributor documentation (Markdown)
│── scripts/             # Legacy launcher scripts
│── README.md
│── requirements.txt
│── .env.example
```

---

## Documentation

- **User Documentation:** [`docs/`](docs/index.html) — architecture, configuration, protocol, troubleshooting, comparison (HTML pages with navigation)
- **Contributor Wiki:** [`wiki/`](wiki/index.md) — setup guide, design decisions, development workflow, FAQ, changelog, roadmap (Markdown pages)

---

## Future Improvements

- Add middle click and back/forward navigation buttons
- Implement acceleration curves, flick scroll, and momentum
- Add polling rate control and real-time rate monitoring
- Support Bluetooth and LAN discovery for zero-config connection
- Add remappable buttons, macro editor, and onboard profile storage
- Develop ergonomic UI themes, palm rejection, and grip calibration

---

## Contributing

Contributions are welcome. Read the [wiki](wiki/index.md) to get started. Feel free to open an issue or submit a pull request.

---

## License

This project is licensed under the MIT License.

---

## Author

**learnerforge**

GitHub: https://github.com/learnerforge
