# Architecture

**Version:** v1.0.0  
**Last updated:** 2026-06-26

This document describes the system architecture of Remote Mouse — how components fit together, data flow, and design decisions for the current version.

---

## System Overview

Remote Mouse follows a simple client-server architecture. The Python server runs on the laptop and serves a web page. The phone connects over WebSocket and sends touch events. The server translates those into OS-level mouse and keyboard actions via `pyautogui`.

There is no database, no persistent storage (beyond `events.log` and `.tunnel_url`), and no authentication. The design prioritizes zero phone installation and minimal latency.

### Project Structure

```
Remote_Mouse/
  src/                  Python source
    server.py             Flask + Flask-SocketIO + pyautogui + cloudflared + setup API
    cli.py                REPL control panel, subprocess manager, live logs
    email_service.py      SMTP sender, importable + CLI modes
  frontend/             Web frontend
    index.html            Main mouse control (touchpad, buttons, media, link)
    setup.html            3-step wizard (connection, email, live logs, redirect)
    static/
      socket.io.min.js    Socket.IO v4.7.5 (49 KB, served locally)
  docs/                 Documentation
    ARCHITECTURE.md
    CONFIGURATION.md
    PROTOCOL.md
    TROUBLESHOOTING.md
    COMPARISON.md
  .env.example          SMTP config template
  events.log            Runtime event log (gitignored)
  .tunnel_url           Cloudflare tunnel URL (gitignored)
  AGENTS.md             LLM agent conventions
```

---

## High-Level Architecture

```mermaid
graph TB
    subgraph Phone["Phone Browser"]
        HTML["index.html<br/>HTML + CSS + JS"]
        SIO["Socket.IO Client<br/>socket.io.min.js"]
        EVT["Touch Events<br/>touchstart/move/end"]
        UI["UI Pages<br/>Touchpad | Media | Link"]
        HTML --> SIO
        EVT --> SIO
        UI --> EVT
    end

    subgraph Laptop["Laptop (Server)"]
        subgraph Python["Python Server"]
            FLASK["Flask HTTP<br/>Port 5000"]
            WS["Flask-SocketIO<br/>WebSocket"]
            API["REST API<br/>/api/*"]
            PYG["pyautogui<br/>OS Control"]
            LOG["Logger<br/>stdout + events.log"]
            FLASK --> WS
            FLASK --> API
            WS --> PYG
            PYG --> LOG
        end
        subgraph Tunnel["Optional Tunnel"]
            CF["cloudflared<br/>trycloudflare.com"]
        end
        subgraph CLI["CLI Control Panel"]
            REPL["REPL Loop<br/>commands: status/log/clear"]
            READER["stdout Reader<br/>colorized output"]
        end
        Python --> CF
        Python --> CLI
    end

    SIO -- "WebSocket Events<br/>mouse_move, click, scroll, media" --> WS
    Phone -- "HTTP GET<br/>index.html, setup.html" --> FLASK
    CF -- "HTTPS Tunnel<br/>*.trycloudflare.com" --> Phone
```

---

## Component Breakdown

### 1. Frontend (`frontend/index.html`)

Single HTML file containing all UI markup, inline CSS, and client-side JavaScript. No build step, no external runtime dependencies except the local Socket.IO library.

#### Pages

```mermaid
graph LR
    subgraph App["index.html - Single Page App"]
        SB["Status Bar<br/>Connection dot + IP"]
        TP["Touchpad<br/>1-finger move<br/>2-finger scroll<br/>tap click"]
        CB["Click Bar<br/>Left | Drag | Right"]
        MP["Media Page<br/>Play/Pause | Next/Prev<br/>Vol Up/Down | Mute"]
        LP["Link Page<br/>Tunnel URL + Copy<br/>Email Request Form"]
        SP["Sensitivity Panel<br/>Slider 0.2x–3.0x"]
        BN["Bottom Nav<br/>Touchpad | Media | Link"]
    end

    BN --> TP
    BN --> MP
    BN --> LP
    TP --> CB
    TP --> SP
```

#### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **No build step** | Served as-is. No npm, webpack, vite on the laptop |
| **Local socket.io (49 KB)** | Eliminates 3-minute CDN load on phone hotspot |
| **Touch Events API** | Broader mobile compatibility than Pointer Events |
| **WebSocket-first transport** | `['websocket', 'polling']` — instant connect, polling fallback |
| **Script at bottom of `<body>`** | Page renders before 49 KB library downloads |
| **touch-action: manipulation** | Prevents double-tap zoom on mobile |
| **appearance: none on slider** | Firefox compatibility for sensitivity slider |
| **Haptic feedback** | `navigator.vibrate(10)` on clicks (not on iOS) |

### 2. Server (`src/server.py`)

Python application built on Flask + Flask-SocketIO with eventlet async mode. Serves frontend, manages WebSocket connections, and executes OS control via pyautogui.

#### Internal Architecture

```mermaid
graph TB
    subgraph Server["server.py"]

        subgraph HTTP["HTTP Layer (Flask)"]
            INDEX["GET /<br/>index.html"]
            SETUP["GET /setup<br/>setup.html"]
            STATIC["GET /static/*<br/>socket.io.min.js"]
            FAVICON["GET /favicon.ico<br/>204 No Content"]
            API_TUNNEL["GET /api/tunnel-url<br/>{url, local_ip}"]
            API_SEND["POST /api/send-url<br/>Email tunnel URL"]
            API_START["POST /api/setup-start<br/>Begin setup"]
            API_STATUS["GET /api/setup-status<br/>Setup progress"]
        end

        subgraph WS["WebSocket Layer (Flask-SocketIO)"]
            CONN["connect<br/>→ screen_info"]
            DISCONN["disconnect"]
            MOVE["mouse_move<br/>→ pyautogui.moveRel"]
            CLICK["click<br/>→ pyautogui.click"]
            SCROLL["scroll<br/>→ pyautogui.scroll"]
            MEDIA["media<br/>→ pyautogui.press"]
            REQ_TUNNEL["request_tunnel_url<br/>→ tunnel_url"]
        end

        subgraph SYS["System Integration"]
            PYGUY["pyautogui<br/>FAILSAFE=False, PAUSE=0"]
            CF_MGR["cloudflared Manager<br/>find → start → monitor (30s timeout)"]
            LOGGER["Logger<br/>_log() → stdout + events.log"]
            SETUP_STATE["Setup State<br/>deque(maxlen=100)"]
        end

        WS --> PYGUY
        WS --> LOGGER
        HTTP --> LOGGER
        API_START --> SETUP_STATE
        API_START --> CF_MGR
        CF_MGR --> LOGGER
    end
```

#### WebSocket Event Handlers

| Event | Handler | Action |
|-------|---------|--------|
| `connect` | `handle_connect` | Send screen dimensions, local IP, tunnel URL |
| `disconnect` | `handle_disconnect` | Log disconnection |
| `mouse_move` | `handle_move` | `pyautogui.moveRel(dx, dy)` |
| `click` | `handle_click` | `pyautogui.click(button)` |
| `scroll` | `handle_scroll` | `pyautogui.scroll(clicks)` — converts px to notches |
| `media` | `handle_media` | `pyautogui.press(playpause/nexttrack/etc.)` |
| `request_tunnel_url` | `handle_request_tunnel_url` | Emit current tunnel URL |

#### Design Decisions

| Decision | Rationale |
|----------|-----------|
| **eventlet.monkey_patch()** | Enables native WebSocket; without it Flask-SocketIO falls to HTTP-long-polling |
| **static_folder=None** | Bypasses Flask 3.0's built-in handler which intercepts `/static/` before our route |
| **Cache-Control: no-cache** on HTML | Prevents cached stale frontend |
| **Cache-Control: max-age=86400** on static | socket.io.min.js cached 24h on phone |
| **pyautogui.FAILSAFE = False** | Prevents corner-movement crash |
| **pyautogui.PAUSE = 0** | Removes 100ms built-in delay between calls |
| **cloudflared via subprocess.Popen** | Non-blocking tunnel management; 30s timeout with regex URL detection |

### 3. CLI Control Panel (`src/cli.py`)

Interactive REPL that launches `server.py` as a subprocess, captures stdout in real-time, and provides filtered colored display.

```mermaid
graph TB
    subgraph CLI["cli.py Process"]
        START["Start<br/>subprocess.Popen(server.py -u)"]
        READER["stdout Reader Thread<br/>colorize() → print"]
        REPL["Main Thread<br/>input() loop"]
        CMD_STATUS["status cmd<br/>→ /api/tunnel-url"]
        CMD_LOG["log cmd<br/>→ tail events.log"]
        CLEANUP["atexit<br/>terminate → wait(5) → kill"]
    end

    subgraph Server["server.py Process"]
        STDOUT["stdout<br/>_log() output"]
        LOGFILE["events.log"]
    end

    START --> Server
    Server --> STDOUT --> READER
    CMD_LOG --> LOGFILE
    CLEANUP --> Server
```

#### Commands

| Command | Description |
|---------|-------------|
| `status` or `s` | Show server status, local IP, tunnel URL |
| `log` or `l` | Show last 20 lines from `events.log` |
| `la` | Show ALL lines from `events.log` |
| `clear` or `cls` | Clear terminal screen |
| `help` or `h` | Show command reference |
| `q` or `exit` | Stop server and quit |

#### Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Subprocess (not threading)** | Flask-SocketIO has known threading issues; separate process avoids GIL |
| **`-u` flag** | Unbuffered Python output ensures real-time log capture |
| **`atexit` cleanup** | Ensures server process is killed even if CLI crashes |
| **`TimeoutExpired → .kill()`** | Fallback if graceful terminate fails |
| **Filtered display** | Hides INFO (mouse moves, scrolls) from live terminal; shows only OK/WARN/ERROR |
| **Colorama** | Cross-platform colored terminal output |

### 4. Email Service (`src/email_service.py`)

Standalone module for sending email via SMTP. Imported by `server.py`, also runnable from CLI.

```mermaid
graph TB
    subgraph email_service.py
        LOAD_ENV["load_env()<br/>.env → dict"]
        BUILD["build_url_email()<br/>HTML + plain text<br/>MIME multipart"]
        SEND["send_email()<br/>SMTP STARTTLS(587)<br/>3 retries"]
    end

    subgraph .env["PROJECT_ROOT/.env"]
        SMTP_HOST
        SMTP_PORT
        SMTP_USERNAME
        SMTP_PASSWORD
    end

    subgraph Usage["Usage Modes"]
        IMPORTED["server.py import<br/>api_send_url route"]
        CLI_SEND["python email_service.py --send <url>"]
        CLI_TEST["python email_service.py --test"]
    end

    LOAD_ENV --> .env
    BUILD --> SEND
    IMPORTED --> BUILD
    CLI_SEND --> BUILD
    CLI_TEST --> SEND
```

#### Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Plain-text MIME alternative** | Ensures deliverability to SMS gateways that strip HTML |
| **Importable by server.py** | `api_send_url` calls `send_email()` directly with tunnel URL |
| **Standalone CLI** | Test SMTP config without starting full server |
| **Standard library only** | `smtplib` + `ssl` — zero external dependencies |
| **3 retries with exponential backoff** | Resilient to transient SMTP failures |

### 5. Cloudflare Tunnel (cloudflared)

External binary creating a secure HTTPS tunnel from Cloudflare's edge to `localhost:5000`.

```mermaid
graph LR
    PHONE["Phone Browser<br/>Internet"] -- "HTTPS" --> CF["Cloudflare Edge<br/>trycloudflare.com"]
    CF -- "Tunnel" --> CF_BIN["cloudflared<br/>on Laptop"]
    CF_BIN -- "localhost:5000" --> SERVER["Python Server"]
```

Provides:
- Public HTTPS URL on any network
- No port forwarding, no static IP, no DNS config
- DDoS protection and edge caching

**Limitations:**
- URL changes on every restart (free tier)
- Idle timeout after several hours
- Adds 50–200 ms latency vs local access

---

## Data Flow

### Connection Sequence

```mermaid
sequenceDiagram
    participant Phone
    participant Flask as Flask HTTP
    participant WS as Flask-SocketIO
    participant PYG as pyautogui
    participant LOG as Logger

    Phone->>Flask: GET /
    Flask-->>Phone: index.html (no-cache)
    Phone->>Flask: GET /static/socket.io.min.js
    Flask-->>Phone: socket.io.min.js (max-age=86400)

    Phone->>WS: WebSocket connect()
    WS->>PYG: pyautogui.size()
    WS-->>Phone: screen_info {width, height, ip, tunnel_url}
    WS->>LOG: log_ok("Client connected")

    Note over Phone,WS: Ready for interaction
```

### Mouse Move Flow

```mermaid
sequenceDiagram
    participant Touch as Phone Touchscreen
    participant JS as index.html JS
    participant WS as Flask-SocketIO
    participant PYG as pyautogui
    participant LOG as Logger

    Touch->>JS: touchmove {dx, dy}
    JS->>JS: Apply sensitivity multiplier
    JS->>JS: Check drag mode (1.2x if active)
    JS->>WS: socket.emit("mouse_move", {dx, dy})
    WS->>PYG: moveRel(int(dx), int(dy))
    PYG-->>WS: cursor moved
    WS->>LOG: log_info("move (+0012, -0005)")
```

### Click Flow

```mermaid
sequenceDiagram
    participant Touch as Phone Touchscreen
    participant JS as index.html JS
    participant WS as Flask-SocketIO
    participant PYG as pyautogui

    Touch->>JS: touchend
    JS->>JS: Check duration < 400ms & no movement
    JS->>JS: navigator.vibrate(10)
    JS->>WS: socket.emit("click", {button: "left"})
    WS->>PYG: click(button="left")
```

### Two-Finger Scroll Flow

```mermaid
sequenceDiagram
    participant Touch as Phone Touchscreen
    participant JS as index.html JS
    participant WS as Flask-SocketIO
    participant PYG as pyautogui

    Touch->>JS: touchstart (2 fingers)
    JS->>JS: Track finger 1 + finger 2 positions
    Touch->>JS: touchmove (2 fingers)
    JS->>JS: Calculate dy delta from both fingers
    JS->>WS: socket.emit("scroll", {dy})
    WS->>PYG: scroll(clicks)  # dy/20 = notches
```

### Setup Wizard Flow

```mermaid
sequenceDiagram
    participant Phone as Phone Browser
    participant Flask as Flask HTTP
    participant WS as Flask-SocketIO
    participant CFM as cloudflared Manager
    participant EMAIL as email_service

    Phone->>Flask: GET /setup
    Flask-->>Phone: setup.html (no-cache)

    Phone->>Flask: POST /api/setup-start {case, email?}
    Flask-->>Phone: {success: true}
    Flask->>Flask: Run setup in daemon thread
    loop Every 1s
        Phone->>Flask: GET /api/setup-status
        Flask-->>Phone: {running, done, logs[], error}
    end

    alt Case: localhost
        Flask->>Flask: Log "Open http://127.0.0.1:5000"
    else Case: same-wifi
        Flask->>Flask: Log "Open http://{ip}:5000"
    else Case: remote
        Flask->>CFM: start_cloudflared()
        CFM-->>Flask: tunnel URL
        Flask->>EMAIL: send_email(url, recipient)
        Flask->>Flask: Log tunnel URL + email status
    end

    Phone-->>Phone: Redirect to index.html
```

---

## Logging Architecture

```mermaid
graph TB
    subgraph Server["server.py"]
        LOG["_log(level, msg)"]
        STDOUT["print(msg, flush=True)"]
        FILE["events.log (append)"]
        LOG --> STDOUT
        LOG --> FILE
    end

    subgraph CLI["cli.py"]
        PIPE["stdout pipe reader"]
        COLOR["colorize()"]
        DISPLAY["Terminal display<br/>OK=green WARN=yellow ERROR=red"]
        TAIL["cmd_log()<br/>→ tail events.log"]
        PIPE --> COLOR --> DISPLAY
        TAIL --> DISPLAY
    end

    subgraph Setup["Setup API"]
        SETUP_LOG["setup_log(msg)"]
        SETUP_QUEUE["setup_state['logs']<br/>deque(maxlen=100)"]
        SETUP_LOG --> STDOUT
        SETUP_LOG --> SETUP_QUEUE
    end
```

---

## Security Model

Remote Mouse has **no authentication**. Security relies on:

1. **Network segmentation** — accessible to anyone on the local network (binds `0.0.0.0:5000`)
2. **URL randomness** — Cloudflare tunnel URLs have ~64-bit entropy
3. **URL volatility** — tunnel URL invalid when cloudflared stops
4. **Trust model** — designed for personal use on trusted networks

For additional security, consider:
- Running behind a reverse proxy with basic auth
- Firewall rules restricting access to specific IPs
- Binding to a specific interface instead of `0.0.0.0`

---

## Threading Model

```mermaid
graph TB
    subgraph Main["Main Thread"]
        SOCKETIO["socketio.run()<br/>Flask + WebSocket"]
    end
    subgraph Daemon["Daemon Threads"]
        CF_READER["cloudflared stdout reader<br/>(start_cloudflared)"]
        SETUP_RUNNER["Setup runner<br/>(api_setup_start)"]
    end
    subgraph CLI["CLI Process (separate)"]
        CLI_MAIN["REPL input() loop"]
        CLI_READER["stdout reader thread"]
    end
```

- **server.py** runs in its own process
- **cli.py** runs as a separate process, connected via pipe to server's stdout
- Setup runs in a daemon thread so the API response returns immediately
- cloudflared stdout reader runs in a daemon thread for non-blocking URL detection
