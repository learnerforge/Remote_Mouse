# Architecture

## Overview

TouchMorph uses a client-server architecture where the Android phone browser is the client and the PC runs the server. Communication happens over a single Socket.IO WebSocket connection.

## Server Components

### `main.py` — Entry Point
Creates the aiohttp web server and Socket.IO async server. Routes HTTP requests and binds Socket.IO events to `TouchMorphSocket` handlers. Runs the cleanup loop and graceful shutdown.

**Key objects:**
- `config: Config` — Global configuration from env vars
- `email_service: EmailService` — SMTP email sender
- `touchmorph: TouchMorphSocket` — All WebSocket event handlers
- `sio: AsyncServer` — Socket.IO server instance
- `app: web.Application` — aiohttp application

### `config.py` — Configuration
Loads environment variables from `.env` file. The `Config` class provides all settings with defaults:
- `TOUCHMORPH_HOST` / `TOUCHMORPH_PORT` — Server bind address
- `SMTP_*` — Email configuration
- `ADMIN_PASSWORD` / `ADMIN_SECRET` — Dashboard auth

### `socket_handler.py` — Event Handlers
The `TouchMorphSocket` class handles all 30+ Socket.IO events. Each handler:
1. Checks rate limit (`_check_rate`) and active status (`_is_active`)
2. Validates input (type checks, enum validation)
3. Performs the action via `MouseController`
4. Logs the event via `_log` (which writes to audit_logs)

**Session lifecycle:**
```
Client connects → on_connect (creates in-memory session)
Client emits session_restore → on_session_restore (restores or creates DB session)
Client pairs → on_pair_request + on_pair_verify
Client switches mode → on_mode_switch
Client disconnects → on_disconnect (touches DB, cleans up)
```

### `mouse_controller.py` — Mouse Wrapper
Wraps `pyautogui` with graceful fallback (preview mode when pyautogui not installed). All mouse/keyboard actions go through here.

### `gesture_processor.py` — Gesture Recognition
Two classes:
- **`GestureProcessor`** — Multi-touch gesture recognition: swipe, pinch, shake, tap, double-tap, long-press, n-finger swipe
- **`SmartScrollEngine`** — Momentum-based scrolling with configurable sensitivity, decay, and inversion

### `session_store.py` — Database Layer
SQLite-based persistence with three tables:
- **sessions** — Device sessions (token, paired state, mode, last_active)
- **logs** — Legacy event logs (backward compatible)
- **audit_logs** — Structured audit log with category/severity/search

Indexes on `audit_logs`: token, category, severity, ts.

### `email_service.py` — Email Sender
SMTP email delivery using `smtplib`. Supports three port modes:
- **465** — SMTP_SSL (implicit TLS)
- **587** — SMTP + STARTTLS (explicit TLS)
- **25** — Plain SMTP (no auth/TLS)

3 retry attempts with exponential backoff. Prints URL to console if email fails.

## Client Components

### `useSocket.ts` — Socket.IO Hook
Central connection management. On mount:
1. Connects to server
2. Emits `session_restore` with saved localStorage token
3. Listens for `session:created` or `session:restored` response
4. Sets up 25-second ping interval

### `App.tsx` — Root Component
Three states:
1. **Not connected** — Shows "Connecting..."
2. **Not paired** — Shows pairing UI (generate code, enter code)
3. **Paired** — Shows mode UI + BottomNav

### Mode Pages
Each page is a self-contained component receiving an `emit` function and optional screen dimensions:

| Page | Events Emitted | Props |
|------|---------------|-------|
| `MouseMode.tsx` | `mouse_event`, `mouse_hold`, `mouse_release`, `mouse_drag`, `click_left`, `click_right`, `click_double`, `gesture_n_finger_swipe` | emit |
| `TouchpadMode.tsx` | `touchpad_event`, `smart_scroll_start/move/end`, `smart_scroll_config`, `gesture_n_finger_swipe` | emit |
| `AirMouseMode.tsx` | `airmouse_move`, `airmouse_click` | emit, screenW, screenH |
| `PresentationMode.tsx` | `presentation_action` | emit |
| `MediaController.tsx` | `media_action` | emit |
| `Settings.tsx` | `smart_scroll_config` | emit |

## Event Flow

```
Phone                    Server
  │                        │
  ├── session_restore ────►├── restore_session() / create_session()
  │◄──── session:created ──┤
  │◄──── session:restored ─┤
  │                        │
  ├── pair_request ───────►├── generate 6-digit code
  │◄────── pair:code ──────┤
  ├── pair_verify ────────►├── verify code, set paired=1
  │◄──── pair:success ─────┤
  │                        │
  ├── mode_switch ────────►├── update mode, emit mode:switched
  │◄──── mode:switched ────┤
  │                        │
  ├── mouse_event ────────►├── move/click/scroll via pyautogui
  ├── touchpad_event ─────►├── relative move + edge scroll
  ├── airmouse_move ──────►├── absolute/relative positioning
  ├── presentation_action ►├── keyboard shortcuts (F5, Esc, arrows)
  └── media_action ───────►├── media keys (playpause, volume, etc.)
```

## Data Flow: Pairing

```
┌─────────┐                    ┌──────────┐                    ┌────────┐
│  Phone  │                    │  Server  │                    │  SQLite │
└────┬────┘                    └────┬─────┘                    └────┬───┘
     │                              │                              │
     │  pair_request                │                              │
     ├─────────────────────────────►│                              │
     │                              │  generate 6-digit code       │
     │◄───── pair:code {code} ──────┤                              │
     │  User sees code on phone     │                              │
     │  User enters code on PC...   │                              │
     │  pair_verify {code}          │                              │
     ├─────────────────────────────►│                              │
     │                              │  verify code matches         │
     │                              │  UPDATE sessions SET paired=1│
     │                              ├─────────────────────────────►│
     │◄──── pair:success ───────────┤                              │
     │                              │                              │
```

## Security

- **Pairing**: 6-digit code, one-time use, generated per session
- **Rate limiting**: Token bucket (60 events/sec), 5-second cooldown warning
- **Input validation**: Type checks, enum whitelists (`VALID_MODES`, `VALID_BUTTONS`, `VALID_DIRECTIONS`)
- **Admin auth**: HMAC-SHA256 signed cookie, 24-hour expiry
- **Session isolation**: `_is_active()` checks `paired` flag before allowing control
- **Audit trail**: All events logged with category, severity, IP, device name
