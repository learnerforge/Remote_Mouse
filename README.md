# Remote Mouse

Turn your phone into a wireless mouse and media remote for your laptop. Zero phone installation — the laptop runs a Python server (Flask + SocketIO + pyautogui), the phone just opens a URL. Touchpad with DPI presets, two-finger scroll, media controls, and optional Cloudflare tunnel for remote access.

<div align="center">
  <img src="https://img.shields.io/badge/python-3.12-blue?logo=python" alt="Python 3.12"/>
  <img src="https://img.shields.io/badge/Flask-000?logo=flask" alt="Flask"/>
  <img src="https://img.shields.io/badge/Socket.IO-010101?logo=socket.io" alt="Socket.IO"/>
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?logo=javascript&logoColor=000" alt="JavaScript"/>
  <img src="https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=fff" alt="HTML5"/>
  <img src="https://img.shields.io/badge/CSS3-1572B6?logo=css3" alt="CSS3"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License"/>
</div>

---

## Features

- **Touchpad** — drag to move the cursor, tap to click, two-finger scroll
- **Click Bar** — left, right, and DPI preset (400/800/1600/3200) buttons
- **Media Remote** — play/pause, next/previous track, volume up/down, mute
- **Sensitivity Control** — adjustable cursor speed (0.2x to 3.0x)
- **Setup Wizard** — 3-step connection guide at `/setup` with live log output
- **Tunnel URL Delivery** — auto-emails the Cloudflare tunnel URL to your phone
- **REPL Control Panel** — interactive terminal with status, live logs, and server management

---

## Quick Start

```bash
git clone https://github.com/learnerforge/Remote_Mouse.git
cd Remote_Mouse
pip install -r requirements.txt

# Start with REPL control panel (recommended)
python src/cli.py
```

Open `http://localhost:5000/setup` on your laptop, pick a connection type, then open the shown URL on your phone and enter the 6-character pairing code displayed in the server terminal. Full setup, prerequisites, and SMTP/cloudflared configuration: [wiki/SETUP.md](wiki/SETUP.md).

---

## Documentation

| Resource | What's inside |
|----------|---------------|
| [`docs/`](docs/index.html) | User docs — architecture, configuration, protocol, troubleshooting (HTML) |
| [`wiki/`](wiki/index.md) | Contributor docs — setup, design decisions, development workflow, FAQ, changelog, roadmap (Markdown) |

Security details live in [docs/architecture.html](docs/architecture.html) (user) and [wiki/ARCHITECTURE.md](wiki/ARCHITECTURE.md) (contributor). At a glance: pairing authentication, rate limiting, CORS origin validation, key-combo blocklist, PII-redacted logging, and security headers.

---

## Roadmap

See [wiki/PLAN.md](wiki/PLAN.md) and [version_control.md](version_control.md) for the versioned feature roadmap and change history.

---

## Contributing

Contributions are welcome. Read the [wiki](wiki/index.md) to get started, then open an issue or submit a pull request.

---

## License

This project is licensed under the MIT License.

## Author

**learnerforge** — https://github.com/learnerforge
