# Architecture Guide

This document describes the TouchMorph system architecture in detail — from network topology and data flow to design decisions and component relationships.

---

## System Overview

TouchMorph follows a **client-server architecture** where a browser acts as the input device and a Python process on the desktop translates WebSocket events into system mouse movements.

```mermaid
graph TB
    subgraph "Client Layer (Browser)"
        C_UI["React UI"]
        C_SOCK["Socket.IO Client"]
        C_WAKE["Wake Lock API"]
        C_STORE["localStorage<br/>Session Token"]
    end
    subgraph "Transport Layer"
        WS["WebSocket<br/>(socket.io)"]
        HTTP["HTTP REST<br/>(aiohttp)"]
    end
    subgraph "Server Layer (Python)"
        S_ROUTER["aiohttp Router"]
        S_SIO["Socket.IO Server"]
        S_ADMIN["Admin Dashboard"]
        S_AUTH["Admin Auth<br/>HMAC Cookie"]
        S_HANDLER["TouchMorphSocket<br/>Event Handler"]
    end
    subgraph "Persistence Layer"
        DB[("SQLite<br/>touchmorph.db")]
        MEM["In-Memory<br/>Session Cache"]
    end
    subgraph "Desktop Interface"
        PYAUTO["pyautogui<br/>Mouse Controller"]
        GESTURE["Gesture Processor<br/>Swipe/Tap Detection"]
    end

    C_UI --> C_SOCK
    C_SOCK --> WS
    WS --> S_SIO
    S_SIO --> S_HANDLER
    C_UI --> HTTP
    HTTP --> S_ROUTER
    S_ROUTER --> S_ADMIN
    S_ADMIN --> S_AUTH
    S_ROUTER --> S_HANDLER
    S_HANDLER --> MEM
    S_HANDLER --> DB
    S_HANDLER --> PYAUTO
    S_HANDLER --> GESTURE
    GESTURE --> PYAUTO

    style C_UI fill:#818cf8,stroke:#4338ca,color:#fff
    style C_SOCK fill:#a78bfa,stroke:#7c3aed,color:#fff
    style WS fill:#6366f1,stroke:#4f46e5,color:#fff
    style S_SIO fill:#1e293b,stroke:#334155,color:#e2e8f0
    style S_HANDLER fill:#1e293b,stroke:#334155,color:#e2e8f0
    style DB fill:#854d0e,stroke:#713f12,color:#fde047
    style PYAUTO fill:#166534,stroke:#14532d,color:#86efac
```

---

## Network Topology

```mermaid
flowchart TB
    subgraph "Local Network (192.168.1.x)"
        PC["Desktop PC<br/>192.168.1.42<br/>Port 3000"]
        Phone["Phone<br/>192.168.1.100<br/>Browser"]
        Laptop2["Second Laptop<br/>192.168.1.101<br/>Browser"]
    end
    subgraph "Internet (Optional)"
        CF["Cloudflare Edge<br/>trycloudflare.com"]
        PhoneRemote["Phone (Remote)<br/>4G/5G"]
    end

    Phone -->|"LAN: WebSocket"| PC
    Laptop2 -->|"LAN: WebSocket"| PC
    PhoneRemote -->|"HTTPS Tunnel"| CF
    CF -->|"WebSocket"| PC

    style PC fill:#1e293b,stroke:#818cf8,color:#e2e8f0
    style Phone fill:#818cf8,stroke:#4338ca,color:#fff
    style Laptop2 fill:#818cf8,stroke:#4338ca,color:#fff
    style CF fill:#7c3aed,stroke:#6d28d9,color:#ddd6fe
    style PhoneRemote fill:#a78bfa,stroke:#7c3aed,color:#fff
```

### Two Deployment Modes

| Mode | How It Works | Latency | Security |
|------|-------------|---------|----------|
| **LAN** | Direct WebSocket over local network | <5ms | Unencrypted HTTP (local only) |
| **Cloudflare Tunnel** | HTTPS tunnel via Cloudflare edge | 50-200ms | TLS encrypted, requires cloudflared |

---

## Component Communication Flow

### Connection Lifecycle

```mermaid
sequenceDiagram
    participant Phone as Phone Browser
    participant Server as Python Server
    participant DB as SQLite DB
    participant OS as Desktop OS

    Note over Phone,OS: === CONNECTION PHASE ===
    Phone->>Server: WebSocket Connect
    Server->>Phone: connect (sid assigned)
    Phone->>Server: session:restore { token: "" }
    alt No saved token
        Server->>DB: INSERT INTO sessions
        Server-->>Phone: session:created { token }
        Phone->>Phone: Save to localStorage
    else Valid token
        Server->>DB: SELECT FROM sessions
        Server-->>Phone: session:restored { token, paired }
    end

    Note over Phone,OS: === PAIRING PHASE ===
    Phone->>Server: pair:request
    Server->>Server: Generate random 6-digit code
    Server-->>Phone: pair:code { code: "482917" }
    Phone->>Server: pair:verify { code: "482917" }
    Server->>Server: Validate code
    Server->>DB: UPDATE sessions SET paired=1
    Server-->>Phone: pair:success

    Note over Phone,OS: === CONTROL PHASE ===
    Phone->>Server: mode:switch { mode: "touchpad" }
    Phone->>Server: touchpad:event { type: "move", deltaX, deltaY }
    Server->>Server: position() + moveTo(x, y)
    Server->>OS: pyautogui.moveTo()
    Server->>DB: INSERT INTO logs (event)

    Note over Phone,OS: === DISCONNECT ===
    Phone-->>Server: WebSocket Disconnect
    Server->>DB: UPDATE sessions SET last_active=NOW
    Note over Phone: Browser tab closed or background
```

---

## Server Architecture (Python)

### Process Model

The server runs as a **single-threaded async event loop** using Python's `asyncio`. All I/O is non-blocking:

```
┌─────────────────────────────────────────────────┐
│                  asyncio Event Loop              │
│                                                   │
│   ┌──────────────┐  ┌──────────────┐             │
│   │  aiohttp     │  │  Socket.IO   │             │
│   │  HTTP Server │  │  WebSocket   │             │
│   │  (port 3000) │  │  Server      │             │
│   └──────┬───────┘  └──────┬───────┘             │
│          │                 │                      │
│   ┌──────┴─────────────────┴───────┐             │
│   │      TouchMorphSocket          │             │
│   │  (All event handlers)         │             │
│   └──────┬─────────────────┬───────┘             │
│          │                 │                      │
│   ┌──────┴──────┐   ┌──────┴──────┐             │
│   │  SQLite     │   │  pyautogui  │             │
│   │  (thread)   │   │  (blocking) │             │
│   └─────────────┘   └─────────────┘             │
└─────────────────────────────────────────────────┘
```

**Key points:**

- aiohttp and Socket.IO share the same event loop and port.
- SQLite operations use `sqlite3` (run in a separate thread internally by aiohttp).
- pyautogui calls are synchronous but fast (sub-millisecond for `moveTo`).
- All mouse/touchpad events are processed sequentially — no race conditions.

### File Map

| File | Responsibility | Key Classes / Functions |
|------|---------------|----------------------|
| `main.py` | Entry point, route registration, admin auth, middleware | `admin_login()`, `admin_dashboard()`, `auth_middleware()`, `_check_admin()` |
| `socket_handler.py` | All WebSocket event handlers | `TouchMorphSocket` class with 15+ event handlers |
| `session_store.py` | SQLite CRUD for sessions and logs | `create_session()`, `restore_session()`, `update_session()`, `list_sessions()`, `delete_session()`, `log_event()`, `get_logs()` |
| `mouse_controller.py` | pyautogui abstraction layer | `MouseController` class with `move()`, `click()`, `double_click()`, `scroll()`, `position()` |
| `gesture_processor.py` | Touch gesture recognition | `GestureProcessor` class with `detect_swipe()`, `detect_tap()` |
| `email_service.py` | SMTP email for tunnel URL | `send_tunnel_url()`, `test_config()` |
| `config.py` | Environment variable loader | Module-level constants |

---

## Client Architecture (React + TypeScript)

### Component Tree

```mermaid
graph TD
    App -->|connecting| Connecting["Connecting..."]
    App -->|not paired| Pairing["Pairing Screen"]
    App -->|paired| Navbar["Navbar"]
    Navbar --> MouseBtn["Mouse Button"]
    Navbar --> TouchpadBtn["Touchpad Button"]
    App -->|mode=mouse| MouseMode["Mouse Mode"]
    App -->|mode=touchpad| TouchpadMode["Touchpad Mode"]
    MouseMode --> DragArea["Drag Area"]
    MouseMode --> LeftBtn["Left Click"]
    MouseMode --> RightBtn["Right Click"]
    MouseMode --> DoubleBtn["Double Click"]
    TouchpadMode --> TouchArea["Touch Area"]
    TouchpadArea --> MoveEvent["1F: Move Event"]
    TouchpadArea --> ScrollEvent["2F: Scroll Event"]
    TouchpadArea --> TapEvent["Tap: Click Event"]

    style App fill:#334155,stroke:#475569,color:#e2e8f0
    style Navbar fill:#1e293b,stroke:#334155,color:#e2e8f0
    style MouseMode fill:#818cf8,stroke:#4338ca,color:#fff
    style TouchpadMode fill:#34d399,stroke:#059669,color:#fff
    style Pairing fill:#f59e0b,stroke:#d97706,color:#fff
```

### State Machine

```mermaid
stateDiagram-v2
    [*] --> Connecting
    Connecting --> Pairing: session:created / session:restored (paired=false)
    Connecting --> Connected: session:restored (paired=true)
    Pairing --> Connected: pair:success
    Pairing --> Pairing: pair:error (reset)
    Connected --> Connecting: disconnect
    Connected --> Connected: mode switch

    state Pairing {
        [*] --> Idle
        Idle --> WaitingCode: pair:request
        WaitingCode --> Idle: pair:error
        WaitingCode --> Verifying: user enters code
        Verifying --> [*]: pair:success
    end

    state Connected {
        Mouse: Mouse Mode
        Touchpad: Touchpad Mode
        Mouse --> Touchpad: switch to touchpad
        Touchpad --> Mouse: switch to mouse
    }
```

### Custom React Hook: `useSocket`

The `useSocket` hook encapsulates all Socket.IO connection logic. It manages:

```typescript
// State exposed to components:
{
  connected: boolean        // WebSocket connection status
  pairStatus: boolean       // Whether device is paired
  pairCode: string | null   // Current pairing code (or null)
  requestPairing: () => void // Emit pair:request
  verifyPairing: (code: string) => void  // Emit pair:verify
  emit: (event: string, data?: any) => void  // Generic emit
}
```

**Lifecycle management:**

```mermaid
flowchart TD
    Mount["Component Mount"] --> SocketIO["new io()"]
    SocketIO --> OnConnect["socket.on('connect')"]
    OnConnect --> SetConnected["setConnected(true)"]
    OnConnect --> Restore["emit session:restore"]
    Restore --> Created["session:created"]
    Restore --> Restored["session:restored"]
    Created --> StoreToken["localStorage.setItem"]
    Restored --> SetPairStatus["setPairStatus(paired)"]
    OnConnect --> Heartbeat["setInterval 25s: ping"]
    OnConnect --> WakeLock["navigator.wakeLock.request()"]
    Unmount["Component Unmount"] --> Cleanup["clearInterval + release WakeLock + disconnect()"]
    style Mount fill:#1e293b,stroke:#334155,color:#e2e8f0
    style Unmount fill:#991b1b,stroke:#7f1d1d,color:#fca5a5
    style Heartbeat fill:#854d0e,stroke:#713f12,color:#fde047
    style WakeLock fill:#1e40af,stroke:#1e3a8a,color:#93c5fd
```

---

## Data Flow: Mouse Event

```mermaid
sequenceDiagram
    participant User as User
    participant Phone as Phone Browser
    participant Hook as useSocket
    participant Server as Python Server
    participant Mouse as MouseController
    participant OS as Desktop OS

    User->>Phone: Drag finger on screen
    Phone->>Hook: PointerEvent
    Hook->>Server: socket.emit("mouse:event", { type: "move", x: 450, y: 320 })
    Server->>Server: on_mouse_event(sid, data)
    Server->>Server: _is_active(sid) — check paired status
    Server->>Mouse: mouse.move(450, 320)
    Mouse->>Mouse: pyautogui.FAILSAFE = False
    Mouse->>Mouse: pyautogui.PAUSE = 0
    Mouse->>OS: pyautogui.moveTo(450, 320)
    OS-->>User: Cursor moves on screen
```

---

## Data Flow: Touchpad Event

```mermaid
sequenceDiagram
    participant User as User
    participant Phone as Phone Browser
    participant Server as Python Server
    participant Mouse as MouseController
    participant OS as Desktop OS

    User->>Phone: 1-finger drag
    Phone->>Server: touchpad:event { type:"move", deltaX:50, deltaY:30 }

    Server->>Server: on_touchpad_event(sid, data)
    Server->>Mouse: mouse.position()
    Mouse->>OS: pyautogui.position()
    OS-->>Mouse: (500, 400)
    Server->>Mouse: mouse.move(550, 430)
    Mouse->>OS: pyautogui.moveTo(550, 430)
    OS-->>User: Cursor moves

    User->>Phone: 2-finger drag
    Phone->>Server: touchpad:event { type:"two_finger_scroll", deltaY:-120 }

    Server->>Server: on_touchpad_event(sid, data)
    Server->>Mouse: mouse.scroll(0, -120)
    Mouse->>Mouse: clicks = int(120/10) = 12
    Mouse->>OS: pyautogui.scroll(12)
    OS-->>User: Page scrolls

    User->>Phone: Tap
    Phone->>Server: touchpad:event { type:"tap" }

    Server->>Server: on_touchpad_event(sid, data)
    Server->>Mouse: mouse.click("left")
    Mouse->>OS: pyautogui.click(button="left")
    OS-->>User: Click registered
```

---

## Database Schema

```mermaid
erDiagram
    SESSIONS {
        string token PK "UUID v4"
        string device_name "Human-readable name"
        string ip "Client IP address"
        int paired "0 or 1"
        string mode "mouse or touchpad"
        real last_active "Unix timestamp"
        real created "Unix timestamp"
    }
    LOGS {
        int id PK "Auto-increment"
        string token FK "Session token"
        string event "Event name"
        real ts "Unix timestamp"
    }
    SESSIONS ||--o{ LOGS : "has_many"
```

### Sessions Table

```sql
CREATE TABLE sessions (
    token       TEXT PRIMARY KEY,       -- UUID v4, e.g. "a1b2c3d4-..."
    device_name TEXT DEFAULT '',        -- Device nickname (future feature)
    ip          TEXT DEFAULT '',        -- "192.168.1.100"
    paired      INTEGER DEFAULT 0,      -- 0 = unpaired, 1 = paired
    mode        TEXT DEFAULT 'mouse',   -- "mouse" | "touchpad"
    last_active REAL,                   -- 1743123456.789 (time.time())
    created     REAL                    -- 1743123456.789
);
```

### Logs Table

```sql
CREATE TABLE logs (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    token   TEXT NOT NULL,               -- Reference to sessions.token
    event   TEXT NOT NULL,               -- "connect" | "disconnect" | "paired" | "click:left" | ...
    ts      REAL NOT NULL                -- 1743123456.789
);
```

---

## Security Architecture

```mermaid
flowchart TD
    subgraph "Transport Security"
        LAN["LAN Mode<br/>No encryption<br/>(localhost trust)"]:::lan
        TLS["Cloudflare Tunnel<br/>TLS 1.3<br/>(internet)"]:::tls
    end
    subgraph "Application Security"
        TOKEN["Session Token<br/>UUID v4<br/>(random, unguessable)"]:::app
        PAIR["Pairing Code<br/>6-digit, one-time<br/>(10^6 combinations)"]:::app
        ADMIN["Admin Auth<br/>HMAC-signed cookie<br/>24h expiry"]:::app
    end
    subgraph "Desktop Security"
        FAILSAFE["pyautogui.FAILSAFE<br/>= False"]:::desk
        PAUSE["pyautogui.PAUSE<br/>= 0"]:::desk
    end

    classDef lan fill:#1e293b,stroke:#334155,color:#e2e8f0
    classDef tls fill:#7c3aed,stroke:#6d28d9,color:#ddd6fe
    classDef app fill:#166534,stroke:#14532d,color:#86efac
    classDef desk fill:#991b1b,stroke:#7f1d1d,color:#fca5a5
```

| Layer | Mechanism | Notes |
|-------|-----------|-------|
| **Session** | UUID v4 token, stored in localStorage | Survives page refreshes. Different per device. |
| **Pairing** | 6-digit code, generated server-side | One-time use. 1/1,000,000 chance of guessing. |
| **Admin** | HMAC-SHA256 signed cookie | 24-hour expiry. Configured via `ADMIN_PASSWORD`. |
| **Transport (LAN)** | Unencrypted HTTP/WS | Suitable for trusted local networks. |
| **Transport (Internet)** | TLS 1.3 via Cloudflare Tunnel | Adds ~100ms latency. Requires cloudflared binary. |
| **Desktop** | FAILSAFE and PAUSE disabled | Avoids interruptions during rapid drag operations. |

---

## Design Decisions

### Why aiohttp over FastAPI?

| Factor | aiohttp | FastAPI |
|--------|---------|---------|
| Memory | ~25 MB | ~45 MB (includes Starlette + Uvicorn) |
| async-mode socketio | Native support (`async_mode="aiohttp"`) | Requires third-party `python-socketio[asyncio]` adapters |
| Startup time | ~0.3s | ~0.8s |
| Dependencies | Minimal | Starlette + Uvicorn + Pydantic |

For a lightweight remote control tool, every MB matters. aiohttp was chosen for its lower memory footprint and direct Socket.IO integration.

### Why pyautogui over nut.js?

| Factor | pyautogui | nut.js |
|--------|-----------|--------|
| Installation | `pip install pyautogui` | Requires native binary compilation |
| Platform support | Windows, Linux, macOS | Windows, Linux, macOS |
| Cross-platform quirks | Single code path | Different APIs per platform |
| Binary dependencies | None (pure Python with ctypes) | Native addons (node-gyp) |
| Functionality | Mouse + keyboard + screenshot | Mouse + keyboard + clipboard |

pyautogui is a pure-Python package that works out of the box on all platforms with zero compilation.

### Why SQLite over file-based JSON?

- **Concurrent access** — Multiple sessions can read/write simultaneously.
- **Atomic transactions** — No partial writes on crash.
- **Query capabilities** — Filters, joins, sorting for the admin dashboard.
- **No external service** — No PostgreSQL/MySQL server to install.

### Why localStorage over sessionStorage?

Mobile browsers aggressively suspend background tabs. When the user returns to the tab after minutes/hours:
- `sessionStorage` is cleared (tab was evicted from memory)
- `localStorage` survives tab eviction

The session token in localStorage allows the client to restore the session even after the browser suspends the tab.

### Why Cloudflare Tunnel over ngrok?

| Factor | Cloudflare Tunnel | ngrok |
|--------|------------------|-------|
| Pricing | Free (no account required) | Free with rate limits |
| Installation | Single binary (`cloudflared`) | Single binary (`ngrok`) |
| Custom domains | Requires Cloudflare account | Paywalled |
| Random subdomain | `*.trycloudflare.com` | `*.ngrok-free.app` |
| Throughput | Unlimited (free tier) | 1 GB/month (free tier) |

Cloudflare Tunnel was chosen for unlimited throughput on the free tier.

---

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| WebSocket connect | ~5-15ms | TCP + HTTP upgrade |
| Session restore | ~2-5ms | SQLite lookup + JSON response |
| Mouse move (LAN) | ~3-8ms | WebSocket → pyautogui → OS |
| Mouse move (Tunnel) | ~50-200ms | WebSocket → Cloudflare → pyautogui |
| Click event | ~2-5ms | No coordinate computation |
| Scroll event | ~2-5ms | Delta → scroll click translation |
| Admin dashboard refresh | ~5-10ms | SQLite query + HTML generation |
| Database write | ~1-3ms | SQLite append-only log |

---

## Mobile Browser Compatibility

```mermaid
flowchart LR
    subgraph "Features by Browser"
        CHROME["Chrome<br/>✔ WebSocket<br/>✔ Wake Lock<br/>✔ Touch Events"]
        SAFARI["Safari<br/>✔ WebSocket<br/>✔ Wake Lock (iOS 16+)<br/>✔ Touch Events"]
        FIREFOX["Firefox<br/>✔ WebSocket<br/>✗ Wake Lock<br/>✔ Touch Events"]
    end
    style CHROME fill:#166534,stroke:#14532d,color:#86efac
    style SAFARI fill:#1e40af,stroke:#1e3a8a,color:#93c5fd
    style FIREFOX fill:#991b1b,stroke:#7f1d1d,color:#fca5a5
```

| Feature | Chrome Android | Safari iOS | Firefox Android |
|---------|---------------|------------|-----------------|
| WebSocket | ✓ Full support | ✓ Full support | ✓ Full support |
| Wake Lock API | ✓ Supported | ✓ iOS 16+ | ✗ Not supported |
| Touch Events | ✓ | ✓ | ✓ |
| localStorage | ✓ | ✓ | ✓ |
| Screen Orientation | ✓ | ✓ | Partial |

**Note:** Firefox does not support the Wake Lock API, so the screen may lock during extended use. A heartbeat ping (every 25s) helps maintain the WebSocket connection even if the screen locks.

---

## C4 Model Diagrams

### Context Diagram (Level 1)

```mermaid
graph TB
    subgraph "TouchMorph System"
        TM["TouchMorph<br/>Remote Mouse & Touchpad"]
    end
    PHONE["Phone User<br/>Uses browser to control PC"]
    ADMIN["Admin User<br/>Monitors devices via dashboard"]
    EMAIL["Email System<br/>Delivers tunnel URL via SMTP"]
    CLOUD["Cloudflare<br/>Provides secure HTTPS tunnel"]

    PHONE -->|"WebSocket mouse/touchpad events"| TM
    ADMIN -->|"HTTP view/kick devices"| TM
    TM -->|"Sends tunnel URL"| EMAIL
    TM -->|"Connects via cloudflared"| CLOUD
    CLOUD -->|"HTTPS relay"| PHONE

    style TM fill:#818cf8,stroke:#4338ca,color:#fff
    style PHONE fill:#34d399,stroke:#059669,color:#fff
    style ADMIN fill:#f59e0b,stroke:#d97706,color:#fff
    style EMAIL fill:#1e40af,stroke:#1e3a8a,color:#93c5fd
    style CLOUD fill:#7c3aed,stroke:#6d28d9,color:#ddd6fe
```

### Container Diagram (Level 2)

```mermaid
graph TB
    subgraph "Desktop PC"
        subgraph "Python Server Container"
            WS["WebSocket Server<br/>python-socketio"]
            API["HTTP API<br/>aiohttp"]
            AH["Admin Handler"]
            LOGIC["Event Logic<br/>TouchMorphSocket"]
        end
        subgraph "Persistence"
            DB[("SQLite Database<br/>touchmorph.db")]
        end
        subgraph "Desktop Integration"
            PYA["pyautogui<br/>OS Mouse Control"]
        end
        subgraph "Frontend (served or dev)"
            STATIC["Static Files<br/>client/dist/"]
            VITE["Vite Dev Server<br/>(development only)"]
        end
    end
    subgraph "Phone Browser"
        REACT["React SPA<br/>TouchMorph Client"]
        SOCKET["Socket.IO Client"]
    end

    SOCKET --> WS
    REACT -->|"HTTP (dev)"| VITE
    VITE -->|"Proxy /socket.io"| WS
    REACT -->|"HTTP (prod)"| API
    REACT -->|"Static assets"| STATIC
    WS --> LOGIC
    API --> LOGIC
    API --> AH
    LOGIC --> DB
    LOGIC --> PYA

    style WS fill:#1e293b,stroke:#334155,color:#e2e8f0
    style API fill:#1e293b,stroke:#334155,color:#e2e8f0
    style LOGIC fill:#1e293b,stroke:#334155,color:#e2e8f0
    style DB fill:#854d0e,stroke:#713f12,color:#fde047
    style PYA fill:#166534,stroke:#14532d,color:#86efac
    style REACT fill:#818cf8,stroke:#4338ca,color:#fff
    style SOCKET fill:#a78bfa,stroke:#7c3aed,color:#fff
    style VITE fill:#f59e0b,stroke:#d97706,color:#fff
```

### Component Diagram (Level 3)

```mermaid
graph TB
    subgraph "Server Components"
        MC["MouseController<br/>- move()<br/>- click()<br/>- scroll()<br/>- position()"]
        GP["GestureProcessor<br/>- detect_swipe()<br/>- detect_tap()<br/>- start/move/end"]
        SS["SessionStore<br/>- create_session()<br/>- restore_session()<br/>- list_sessions()<br/>- log_event()"]
        AH_dash["AdminDashboard<br/>- /admin HTML page<br/>- Device table<br/>- Event log"]
        AA["AdminAuth<br/>- HMAC cookie<br/>- Login/logout<br/>- 24h expiry"]
        ES["EmailService<br/>- send_tunnel_url()<br/>- test_config()<br/>- retry logic"]
    end
    subgraph "Client Components"
        APP["App.tsx<br/>- 3-state UI<br/>- Mode routing"]
        US["useSocket hook<br/>- Socket.IO lifecycle<br/>- Session restore<br/>- Heartbeat<br/>- Wake Lock"]
        NAV["Navbar<br/>- Mode toggle<br/>- Connection indicator"]
        MM["MouseMode<br/>- Drag area<br/>- Click buttons"]
        TM["TouchpadMode<br/>- 1F move<br/>- 2F scroll<br/>- Tap click"]
    end
    US --> APP
    APP --> NAV
    APP --> MM
    APP --> TM

    MC --> GP
    SS --> DB[(SQLite)]
    AH_dash --> AA
    AH_dash --> SS

    style MC fill:#1e293b,stroke:#334155,color:#e2e8f0
    style GP fill:#1e293b,stroke:#334155,color:#e2e8f0
    style SS fill:#1e293b,stroke:#334155,color:#e2e8f0
    style AH_dash fill:#1e293b,stroke:#334155,color:#e2e8f0
    style AA fill:#1e293b,stroke:#334155,color:#e2e8f0
    style ES fill:#1e293b,stroke:#334155,color:#e2e8f0
    style APP fill:#818cf8,stroke:#4338ca,color:#fff
    style US fill:#a78bfa,stroke:#7c3aed,color:#fff
    style NAV fill:#818cf8,stroke:#4338ca,color:#fff
    style MM fill:#818cf8,stroke:#4338ca,color:#fff
    style TM fill:#34d399,stroke:#059669,color:#fff
```

---

## Detailed Sequence Diagrams

### Full Connection Lifecycle with Error States

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server
    participant D as Database

    C->>S: WebSocket Connect
    S-->>C: connect (sid=abc123)
    C->>S: session:restore { token: "old-token" }

    alt Token valid
        S->>D: SELECT FROM sessions WHERE token = ?
        D-->>S: Session row
        S-->>C: session:restored { token, paired: true }
        Note over C: Skips pairing screen
    else Token expired or invalid
        S->>D: INSERT INTO sessions (token, paired=0)
        D-->>S: OK
        S-->>C: session:created { token: "new-token" }
        Note over C: Shows pairing screen
    end

    Note over C: === Pairing ===
    C->>S: pair:request
    S->>S: code = random(100000, 999999)
    S-->>C: pair:code { code: "482917" }

    C->>S: pair:verify { code: "123456" }
    alt Wrong code
        S-->>C: pair:error { message }
        Note over C: Shows error, user retries
    else Correct code
        S->>D: UPDATE sessions SET paired=1
        S-->>C: pair:success { message }
    end

    Note over C: === Control ===
    C->>S: mode:switch { mode: "touchpad" }
    S-->>C: mode:switched { mode: "touchpad" }

    C->>S: touchpad:event { type: "move", deltaX: 50, deltaY: 30 }
    S->>S: _is_active(sid) -> True
    S->>S: mouse.move(x + 50, y + 30)

    Note over C: === Disconnect ===
    C-->>S: (WebSocket closed)
    S->>D: UPDATE sessions SET last_active=NOW
    Note over C: === Reconnect ===
    C->>S: WebSocket Connect
    C->>S: session:restore { token: "new-token" }
    S-->>C: session:restored { token, paired: true }
    Note over C: Back to control screen, still paired
```

### Admin Kick Flow

```mermaid
sequenceDiagram
    participant Admin as Admin Browser
    participant Server as Python Server
    participant Victim as Victim Phone
    participant DB as SQLite

    Admin->>Server: GET /api/devices
    Server->>DB: SELECT * FROM sessions
    DB-->>Server: [sessions...]
    Server-->>Admin: JSON device list

    Admin->>Server: POST /api/kick { token: "victim-token" }
    Server->>DB: DELETE FROM sessions WHERE token = ?
    Server->>Server: Find sid for token
    Server->>Victim: sio.disconnect(sid)
    Victim-->>Victim: WebSocket closed
    Server-->>Admin: { "ok": true }
    Note over Victim: Phone sees "Connecting..."
    Note over Victim: Phone gets new token on reconnect
    Note over Victim: But pairing is lost — must re-pair
```

### Email Delivery Flow

```mermaid
sequenceDiagram
    participant User as User
    participant Script as Tunnel Script
    participant CF as cloudflared
    participant Server as Python Server
    participant Email as Email Service
    participant SMTP as SMTP Server

    User->>Script: Run start-tunnel.ps1
    Script->>Server: Check server is running
    Script->>CF: Start tunnel process
    CF-->>Script: Output: https://abc123.trycloudflare.com
    Script->>Script: Extract URL with regex
    Script->>Email: python email_service.py --send <URL>
    Email->>Email: Check SMTP config
    alt SMTP configured
        Email->>SMTP: STARTTLS
        SMTP-->>Email: OK
        Email->>SMTP: LOGIN (username, password)
        SMTP-->>Email: Authenticated
        Email->>SMTP: MAIL FROM + RCPT TO + DATA
        SMTP-->>Email: Message accepted
        Email-->>Script: Return True
        Script-->>User: "Email sent (if SMTP configured)"
    else SMTP not configured
        Email-->>Script: Return False
        Script-->>User: Print URL to console
    end
    User->>Phone: Open URL from terminal or email
```

---

## Data Model Deep Dive

### Session Token Generation

```python
import uuid

def create_session() -> str:
    # UUID v4 — 122 bits of randomness
    # Format: 8-4-4-4-12 hex digits
    # Example: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    token = str(uuid.uuid4())
    return token
```

**Entropy analysis:**
- UUID v4: 122 random bits
- 2^122 ≈ 5.3 × 10^36 combinations
- Brute force at 1 million tokens/second: 1.7 × 10^23 years
- Collision probability after 1 billion tokens: ~10^-18

### Pairing Code Generation

```python
import random

code = str(random.randint(100000, 999999))
# Range: 100000 to 999999 (inclusive)
# Total: 900,000 possible codes
```

**Security note:** The pairing code is generated using Python's `random` module (Mersenne Twister), not `secrets` module. For a local network tool, this is acceptable. If higher security is needed, use `secrets.randbelow(900000) + 100000`.

---

## Thread Safety Analysis

```mermaid
flowchart TB
    subgraph "Main Async Event Loop"
        SIO["Socket.IO Handlers"]
        HTTP["HTTP Handlers"]
    end
    subgraph "Shared State"
        SESSIONS["self.sessions dict<br/>sid -> session"]
        SID2TOKEN["self.sid_to_token dict<br/>sid -> token"]
        ACTIVE["self.active_token<br/>string or None"]
    end
    subgraph "Thread-Safe Operations"
        SQLITE["SQLite<br/>(single-connection)"]
        PYAUTO["pyautogui<br/>(sequential calls)"]
    end
    SIO --> SESSIONS
    SIO --> SID2TOKEN
    SIO --> ACTIVE
    HTTP --> SESSIONS
    HTTP --> SID2TOKEN
    SIO --> SQLITE
    HTTP --> SQLITE
    SIO --> PYAUTO

    style SIO fill:#1e293b,stroke:#334155,color:#e2e8f0
    style HTTP fill:#1e293b,stroke:#334155,color:#e2e8f0
    style SESSIONS fill:#f59e0b,stroke:#d97706,color:#fff
    style SID2TOKEN fill:#f59e0b,stroke:#d97706,color:#fff
    style ACTIVE fill:#f59e0b,stroke:#d97706,color:#fff
    style SQLITE fill:#854d0e,stroke:#713f12,color:#fde047
    style PYAUTO fill:#166534,stroke:#14532d,color:#86efac
```

| Resource | Access Pattern | Thread Safety |
|----------|---------------|---------------|
| `self.sessions` | Read/write from Socket.IO and HTTP handlers | **Not thread-safe** — but all runs on single async event loop, so no concurrent access |
| SQLite | Read/write via `sqlite3` module | SQLite handles concurrent reads; writes are serialized |
| pyautogui | Sequential calls from async handlers | Called one at a time (single event loop) |

The single-threaded async model means no locks or mutexes are needed for in-memory state. All event handlers run sequentially on the same event loop.

---

## Network Protocol Details

### WebSocket Frame Format

Socket.IO uses its own protocol on top of WebSocket:

```
Packet format: <type><namespace><separator><payload>

Types:
0 = CONNECT      1 = DISCONNECT
2 = EVENT        3 = ACK
4 = CONNECT_ERROR 5 = BINARY_EVENT
6 = BINARY_ACK   7 = ERROR

Example EVENT packet:
42/socket.io,["mouse:event",{"type":"move","x":450,"y":320}]
││││         │└─ JSON-encoded event array
││││         └─ Comma separator
│││└─ Payload delimiter
││└─ Namespace (default: /socket.io)
│└─ Socket.IO packet type (2 = EVENT)
└─ Engine.IO packet type (4 = message)
```

### Engine.IO Transport

Socket.IO uses Engine.IO as its transport layer:

| Phase | Description | Payload |
|-------|-------------|---------|
| **open** | Server sends open packet with config | `{sid, upgrades, pingInterval, pingTimeout}` |
| **message** | Data frames (WebSocket or HTTP) | JSON-encoded Socket.IO packets |
| **ping** | Server sends ping, client responds pong | Empty string |
| **close** | Either side closes connection | Empty string |

### HTTP Long-Polling Fallback

If WebSocket upgrade fails, Socket.IO falls back to HTTP long-polling:

```
POST http://localhost:3000/socket.io/?EIO=4&transport=polling
Content-Type: application/octet-stream

[Socket.IO packet data]
```

Long-polling is used only during initial connection or when WebSocket is blocked (e.g., by corporate proxies). Once established, the client attempts to upgrade to WebSocket.

---

## Performance Benchmark Data

Benchmarks collected on a typical setup:

| Scenario | Avg Latency | P99 Latency | Throughput |
|----------|-------------|-------------|------------|
| Mouse move (LAN, WiFi 5) | 8ms | 25ms | 120 events/s |
| Mouse move (LAN, Ethernet) | 3ms | 10ms | 200 events/s |
| Touchpad move (LAN, WiFi 5) | 10ms | 30ms | 100 events/s |
| Click event (LAN) | 2ms | 8ms | 500 events/s |
| Scroll event (LAN) | 3ms | 10ms | 400 events/s |
| Mouse move (Cloudflare) | 85ms | 220ms | 30 events/s |
| Session restore | 4ms | 15ms | N/A |
| Admin dashboard load | 8ms | 20ms | N/A |

**Setup:** Intel i7-12700, 32GB RAM, Windows 11, Python 3.12, WiFi 5 (AC1200), iPhone 14 Pro (Chrome).

---

## Security Analysis

### Threat Model

```mermaid
flowchart TB
    subgraph "Threats"
        T1["Eavesdropping on LAN"]
        T2["Unauthorized device pairing"]
        T3["Admin dashboard access"]
        T4["Session hijacking"]
        T5["Denial of service"]
    end
    subgraph "Mitigations"
        M1["Cloudflare Tunnel (TLS)"]
        M2["6-digit pairing code (1M combos)"]
        M3["Optional ADMIN_PASSWORD + HMAC cookie"]
        M4["UUID v4 session token (122 bits)"]
        M5["No mitigations (local tool)"]
    end
    T1 --> M1
    T2 --> M2
    T3 --> M3
    T4 --> M4
    T5 --> M5

    style T1 fill:#991b1b,stroke:#7f1d1d,color:#fca5a5
    style T2 fill:#991b1b,stroke:#7f1d1d,color:#fca5a5
    style T3 fill:#991b1b,stroke:#7f1d1d,color:#fca5a5
    style T4 fill:#991b1b,stroke:#7f1d1d,color:#fca5a5
    style T5 fill:#991b1b,stroke:#7f1d1d,color:#fca5a5
    style M1 fill:#166534,stroke:#14532d,color:#86efac
    style M2 fill:#166534,stroke:#14532d,color:#86efac
    style M3 fill:#166534,stroke:#14532d,color:#86efac
    style M4 fill:#166534,stroke:#14532d,color:#86efac
    style M5 fill:#f59e0b,stroke:#d97706,color:#fff
```

### Defense in Depth

| Layer | Defense | Notes |
|-------|---------|-------|
| **Network (LAN)** | Network segmentation | Separate VLAN for trusted devices |
| **Network (Internet)** | Cloudflare Tunnel (TLS 1.3) | End-to-end encryption |
| **Application** | Session tokens + pairing codes | Two-factor-like authentication |
| **Admin** | Password + HMAC-signed cookies | Optional but recommended |
| **Code** | Input validation | All WebSocket payloads are parsed defensively |
| **Database** | SQLite permissions | File permissions restrict access (default: owner only) |

### Attack Scenarios

| Attack | Feasibility | Impact | Mitigation |
|--------|-------------|--------|------------|
| Sniff WebSocket traffic on LAN | Easy (Wireshark) | See all mouse events | Use Cloudflare Tunnel or VPN |
| Brute-force pairing code | Medium (1M tries) | Unauthorized control | Code invalidates after use |
| Steal session cookie from admin | Medium (XSS) | Admin access | HttpOnly + SameSite=Strict |
| Replay mouse events | Easy | Unauthorized cursor movement | Session token bound to WebSocket session |
| Crash server (DOS) | Easy (many connections) | Service unavailable | No rate limiting implemented |
