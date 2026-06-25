# TouchMorph

Browser-based remote mouse & touchpad system. Turn your Android phone into a wireless input device for your PC.

**No app install needed.** Open a URL, pair, and control.

## Architecture

```
┌──────────────────────┐       Socket.IO        ┌──────────────────────┐
│   Android Phone      │ ◄────── WebSocket ────► │   PC Server          │
│   (React + Vite)     │                         │   (aiohttp + Python) │
│                      │                         │                      │
│   Mouse Mode         │   mouse_event           │   MouseController    │
│   Touchpad Mode      │   touchpad_event        │   (pyautogui)        │
│   Air Mouse Mode     │   airmouse_move         │                      │
│   Presentation Mode  │   presentation_action   │   GestureProcessor   │
│   Media Controller   │   media_action          │   SmartScrollEngine  │
│   Settings           │   system_action         │                      │
└──────────────────────┘                         │   Session Store      │
                                                 │   (SQLite)           │
                          ┌──────────────────────┤                      │
                          │   Cloudflare Tunnel   │   Audit Logging      │
                          │   (cloudflared)       │                      │
                          └──────────────────────┘   Email Service      │
                                                    (smtplib)           │
                                                 └──────────────────────┘
```

## Quick Start

```bash
git clone <repo>
cd Remote_Mouse

# Server setup
pip install -r server/requirements.txt
cp .env.example .env   # edit with your settings
python server/main.py

# Client setup (development only)
cd client
npm install
npm run dev
```

Open `http://localhost:3000` in your phone browser (or the Vite dev URL).

## Project Structure

```
server/
├── config.py              # Environment config class
├── email_service.py       # SMTP email sending
├── gesture_processor.py   # Touch gesture recognition
├── main.py                # HTTP + WebSocket server entry point
├── mouse_controller.py    # pyautogui wrapper
├── requirements.txt       # Python dependencies
├── session_store.py       # SQLite session/log storage
├── socket_handler.py      # All Socket.IO event handlers
└── touchmorph.db          # SQLite database (auto-created)

client/
├── package.json
├── src/
│   ├── App.tsx             # Root component + pairing flow
│   ├── main.tsx            # React entry
│   ├── index.css           # Tailwind imports
│   ├── components/
│   │   └── BottomNav.tsx   # 6-tab navigation bar
│   ├── hooks/
│   │   └── useSocket.ts    # Socket.IO connection hook
│   └── pages/
│       ├── AirMouseMode.tsx      # Tilt-based pointer
│       ├── MediaController.tsx   # Playback + volume
│       ├── MouseMode.tsx         # Touch drag pointer
│       ├── PresentationMode.tsx  # Slide control
│       ├── Settings.tsx          # Preferences
│       └── TouchpadMode.tsx      # Relative pointer + scroll
```

## Features

- **5 control modes**: Mouse, Touchpad, Air Mouse, Presentation, Media
- **Secure pairing**: 6-digit code verification
- **Session persistence**: Survives page refresh/background suspend
- **Rate limiting**: 60 events/sec with cooldown warnings
- **Audit logging**: Full event history with admin dashboard
- **Auto-cleanup**: Stale sessions and logs trimmed automatically
- **Email delivery**: Tunnel URL sent via SMTP on startup
- **Port auto-fallback**: Tries PORT through PORT+9
