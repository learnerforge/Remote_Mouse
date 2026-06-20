# API Reference

Complete documentation of all WebSocket events, HTTP endpoints, and data structures used by TouchMorph.

---

## WebSocket Events

The client-server communication uses **Socket.IO** with WebSocket transport (with long-polling fallback). All events are JSON-encoded.

### Connection Flow

```mermaid
sequenceDiagram
    participant Client
    participant Server

    Client->>Server: connect
    Server-->>Client: connect (sid assigned)
    Client->>Server: session:restore { token }
    alt Token is valid
        Server-->>Client: session:restored { token, paired, mode }
    else Token is empty or invalid
        Server-->>Client: session:created { token }
    end
    Client->>Server: pair:request (optional)
    Server-->>Client: pair:code { code }
    Client->>Server: pair:verify { code }
    alt Code matches
        Server-->>Client: pair:success { message }
    else Code wrong
        Server-->>Client: pair:error { message }
    end
    Client->>Server: mode:switch { mode }
    Server-->>Client: mode:switched { mode, screenWidth, screenHeight }
    loop Control
        Client->>Server: mouse:event / touchpad:event / airmouse:move
        Client->>Server: gesture:start/move/end / presentation:action
        Client->>Server: media:action / smartscroll:start/move/end
        Client->>Server: system:action / screen:info / click:* / scroll
    end
    Client->>Server: ping (heartbeat, volatile)
    Server-->>Client: server:shutdown (on server stop)
    Client->>Server: disconnect
```

---

### Client → Server Events

#### `session:restore`

Restore a previous session or create a new one. Sent immediately on WebSocket connect.

**Payload:**

```json
{
  "token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | No | Previously saved session token. Empty string or omitted to create new session. |

**Server responses:** `session:created` or `session:restored`

---

#### `pair:request`

Request a new 6-digit pairing code.

**Payload:** None

**Server response:** `pair:code`

---

#### `pair:verify`

Submit a pairing code to establish the device as the active controller.

**Payload:**

```json
{
  "code": "482917"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | string | Yes | The 6-digit code displayed on the device that called `pair:request`. |

**Server responses:** `pair:success` or `pair:error`

---

#### `mode:switch`

Switch between available input modes.

**Payload:**

```json
{
  "mode": "touchpad"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | One of: `"mouse"`, `"touchpad"`, `"airmouse"`, `"presentation"`, `"media"`. |

**Server response:** `mode:switched` (now includes `screenWidth` and `screenHeight`)

---

#### `mouse:event`

Send a mouse-related event (move, click, double-click, scroll).

**Payload — Move:**

```json
{
  "type": "move",
  "x": 450,
  "y": 320
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | `"move"`, `"click"`, `"doubleclick"`, or `"scroll"` |
| `x` | number | For move | Absolute X coordinate from phone touch position |
| `y` | number | For move | Absolute Y coordinate from phone touch position |
| `button` | string | For click | `"left"` or `"right"` |
| `deltaX` | number | For scroll | Horizontal scroll delta (used for touchpad-style scroll) |
| `deltaY` | number | For scroll | Vertical scroll delta (used for touchpad-style scroll) |

**Payload — Click:**

```json
{
  "type": "click",
  "button": "right"
}
```

**Payload — Scroll:**

```json
{
  "type": "scroll",
  "deltaY": -120,
  "deltaX": 0
}
```

---

#### `touchpad:event`

Send a touchpad event (relative move, two-finger scroll, tap).

**Payload — Move (1 finger):**

```json
{
  "type": "move",
  "deltaX": 50,
  "deltaY": 30,
  "fingerCount": 1
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | `"move"`, `"tap"`, or `"two_finger_scroll"` |
| `deltaX` | number | For move/scroll | Horizontal delta from last position |
| `deltaY` | number | For move/scroll | Vertical delta from last position |
| `fingerCount` | number | No | Number of fingers detected (1 or 2) |

**Payload — Two-Finger Scroll:**

```json
{
  "type": "two_finger_scroll",
  "deltaX": 0,
  "deltaY": -120,
  "fingerCount": 2
}
```

**Payload — Tap:**

```json
{
  "type": "tap"
}
```

---

#### `click:left`

Trigger a left mouse button click.

**Payload:** None

---

#### `click:right`

Trigger a right mouse button click.

**Payload:** None

---

#### `click:double`

Trigger a double-click (left button).

**Payload:** None

---

#### `scroll`

Trigger a scroll event.

**Payload:**

```json
{
  "deltaY": -120,
  "deltaX": 0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `deltaY` | number | No | Vertical scroll delta. Negative = scroll down. |
| `deltaX` | number | No | Horizontal scroll delta. |

---

#### `ping`

Heartbeat ping to keep the connection alive. Sent as a **volatile** event every 25 seconds — if the connection is congested, the ping is dropped rather than queued.

**Payload:** None (no acknowledgment expected)

---

#### `mouse:event` — drag

Initiates or ends a drag-and-drop operation. Hold mode keeps the button pressed while moving.

**Payload — hold:**

```json
{
  "type": "hold"
}
```

**Payload — release:**

```json
{
  "type": "release"
}
```

**Payload — drag move:**

```json
{
  "type": "drag",
  "x": 500,
  "y": 300
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | `"hold"`, `"release"`, or `"drag"` |
| `x` | number | For drag | Absolute X coordinate |
| `y` | number | For drag | Absolute Y coordinate |

---

#### `gesture:start` / `gesture:move` / `gesture:end`

Multi-touch gesture tracking for advanced gestures (pinch, n-finger swipe, long-press, shake).

**Payload — start:**

```json
{
  "touches": [{ "id": 0, "x": 100, "y": 200 }]
}
```

**Payload — move:**

```json
{
  "touches": [{ "id": 0, "x": 150, "y": 250 }, { "id": 1, "x": 300, "y": 400 }]
}
```

**Payload — end:**

```json
{
  "touches": []
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `touches` | array | Yes | Array of touch objects, each with `id` (int), `x` (number), `y` (number) |

---

#### `gesture:n_finger_swipe`

Detected multi-finger swipe from the gesture processor.

```json
{
  "direction": "right",
  "fingerCount": 3
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `direction` | string | Yes | `"up"`, `"down"`, `"left"`, or `"right"` |
| `fingerCount` | number | Yes | Number of fingers detected (2, 3, 4+) |

**Server-side mapping:** 2F swipe → right-click, 3F swipe → double-click, 4F+ swipe → alt-tab / task view.

---

#### `airmouse:move`

Gyroscope-based pointer movement (Air Mouse mode).

**Payload:**

```json
{
  "alpha": 45.2,
  "beta": 12.8,
  "gamma": -3.1
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `alpha` | number | No | Device orientation alpha (compass heading) |
| `beta` | number | Yes | Device orientation beta (front-back tilt, degrees) |
| `gamma` | number | Yes | Device orientation gamma (left-right tilt, degrees) |

---

#### `presentation:action`

Slide navigation and presentation control.

**Payload:**

```json
{
  "action": "next"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | Yes | `"next"`, `"prev"`, `"black"`, `"white"`, `"start"`, `"escape"`, `"first"`, `"pointer"` |

**Action mapping:** `next` → Page Down, `prev` → Page Up, `black` → B key, `white` → W key, `start` → F5, `escape` → Esc, `first` → Home, `pointer` → holds left click (laser pointer mode).

---

#### `media:action`

Media playback controls.

**Payload:**

```json
{
  "action": "play_pause"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | Yes | `"play_pause"`, `"next"`, `"prev"`, `"vol_up"`, `"vol_down"`, `"mute"` |

---

#### `smartscroll:start` / `smartscroll:move` / `smartscroll:end`

Smart Scroll mode (used by Touchpad mode for momentum scrolling).

**Payload — start:**

```json
{
  "touchId": 0,
  "x": 100,
  "y": 200
}
```

**Payload — move:**

```json
{
  "touchId": 0,
  "x": 150,
  "y": 180
}
```

**Payload — end:**

```json
{
  "touchId": 0
}
```

---

#### `smartscroll:config`

Configure Smart Scroll parameters.

**Payload:**

```json
{
  "sensitivity": 1.0,
  "naturalScroll": false,
  "decay": 0.92
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sensitivity` | number | No | Scroll sensitivity multiplier (default 1.0) |
| `naturalScroll` | boolean | No | Natural (reverse) scroll direction (default false) |
| `decay` | number | No | Momentum decay rate (0.0–1.0, default 0.92) |

---

#### `system:action`

System-level keyboard shortcuts.

**Payload:**

```json
{
  "action": "alt_tab"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | Yes | `"alt_tab"`, `"task_view"`, `"show_desktop"`, `"lock_screen"`, `"copy"`, `"paste"`, `"cut"`, `"undo"`, `"redo"`, `"select_all"`, `"save"`, `"find"`, `"esc"`, `"enter"`, `"fullscreen"` |

---

#### `screen:info`

Request server screen dimensions (returns same data as `mode:switched`).

**Payload:** None

**Server response:** `screen:info` (see Server → Client events)

---

### Server → Client Events

#### `session:created`

Sent when a new session is created (no valid token provided on connect).

```json
{
  "token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "screenWidth": 1920,
  "screenHeight": 1080
}
```

| Field | Type | Description |
|-------|------|-------------|
| `token` | string | The new session UUID. Must be saved to localStorage. |
| `screenWidth` | number | Total screen width in pixels (all monitors) |
| `screenHeight` | number | Total screen height in pixels |

---

#### `session:restored`

Sent when an existing session is successfully restored.

```json
{
  "token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "paired": true,
  "mode": "touchpad",
  "screenWidth": 1920,
  "screenHeight": 1080
}
```

| Field | Type | Description |
|-------|------|-------------|
| `token` | string | The session UUID (may be refreshed by server) |
| `paired` | boolean | Whether the device was already paired |
| `mode` | string | Last used mode: `"mouse"`, `"touchpad"`, `"airmouse"`, `"presentation"`, or `"media"` |
| `screenWidth` | number | Total screen width in pixels |
| `screenHeight` | number | Total screen height in pixels |

---

#### `pair:code`

Sent in response to `pair:request`. Contains the 6-digit pairing code.

```json
{
  "code": "482917"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | 6-digit numeric code. Display this to the user. |

---

#### `pair:success`

Sent when `pair:verify` receives a matching code.

```json
{
  "message": "Device paired successfully"
}
```

The client should enable the main control interface upon receiving this event.

---

#### `pair:error`

Sent when `pair:verify` receives a non-matching code.

```json
{
  "message": "Invalid pairing code"
}
```

The client should clear the code input and allow the user to retry.

---

#### `screen:info`

Server response to `screen:info` request or emitted on connect/session restore.

```json
{
  "screenWidth": 1920,
  "screenHeight": 1080
}
```

| Field | Type | Description |
|-------|------|-------------|
| `screenWidth` | number | Total screen width in pixels (all monitors) |
| `screenHeight` | number | Total screen height in pixels |

---

#### `server:shutdown`

Emitted to all connected clients when the server begins graceful shutdown. Clients should save state and prepare for disconnect.

```json
{
  "message": "Server is shutting down"
}
```

**Client behavior:** Save session token, show "Server offline" message, disable controls.

---

#### `mode:switched`

Confirms the mode switch requested via `mode:switch`. Now includes screen dimensions for Air Mouse absolute positioning.

```json
{
  "mode": "touchpad",
  "screenWidth": 1920,
  "screenHeight": 1080
}
```

| Field | Type | Description |
|-------|------|-------------|
| `mode` | string | The confirmed mode: `"mouse"`, `"touchpad"`, `"airmouse"`, `"presentation"`, or `"media"` |
| `screenWidth` | number | Total screen width in pixels (all monitors) |
| `screenHeight` | number | Total screen height in pixels |

---

### Event Summary

```mermaid
flowchart LR
    subgraph "Client Emits"
        SR["session:restore"]
        PR["pair:request"]
        PV["pair:verify"]
        MS["mode:switch"]
        ME["mouse:event"]
        TE["touchpad:event"]
        AM["airmouse:move"]
        GA["gesture:start/move/end"]
        PA["presentation:action"]
        MA["media:action"]
        SS["smartscroll:start/move/end"]
        SY["system:action"]
        SI["screen:info"]
        CL["click:left"]
        CR["click:right"]
        CD["click:double"]
        SC["scroll"]
        PI["ping"]
    end
    subgraph "Server Emits"
        SCr["session:created"]
        SRe["session:restored"]
        PC["pair:code"]
        PS["pair:success"]
        PE["pair:error"]
        MSw["mode:switched"]
        SIn["screen:info"]
        SSh["server:shutdown"]
    end

    SR --> SCr
    SR --> SRe
    PR --> PC
    PV --> PS
    PV --> PE
    MS --> MSw
    SI --> SIn

    style CL fill:#1e293b,stroke:#818cf8,color:#e2e8f0
    style CR fill:#1e293b,stroke:#818cf8,color:#e2e8f0
    style CD fill:#1e293b,stroke:#818cf8,color:#e2e8f0
    style SC fill:#1e293b,stroke:#818cf8,color:#e2e8f0
    style ME fill:#1e293b,stroke:#34d399,color:#e2e8f0
    style TE fill:#1e293b,stroke:#34d399,color:#e2e8f0
    style AM fill:#1e293b,stroke:#34d399,color:#e2e8f0
    style GA fill:#1e293b,stroke:#34d399,color:#e2e8f0
    style PA fill:#1e293b,stroke:#34d399,color:#e2e8f0
    style MA fill:#1e293b,stroke:#34d399,color:#e2e8f0
    style SS fill:#1e293b,stroke:#34d399,color:#e2e8f0
    style SY fill:#1e293b,stroke:#34d399,color:#e2e8f0
    style SI fill:#1e293b,stroke:#34d399,color:#e2e8f0
    style PI fill:#1e293b,stroke:#64748b,color:#e2e8f0
    style SR fill:#818cf8,stroke:#4338ca,color:#fff
    style PR fill:#f59e0b,stroke:#d97706,color:#fff
    style PV fill:#f59e0b,stroke:#d97706,color:#fff
    style MS fill:#818cf8,stroke:#4338ca,color:#fff
```

---

## HTTP API Endpoints

### `GET /health`

Health check endpoint. Returns server status.

**Response 200:**

```json
{
  "status": "ok"
}
```

---

### `GET /admin`

The TouchMorph admin dashboard. Returns an HTML page with device monitoring and event logs.

**Authentication:** Required if `ADMIN_PASSWORD` is set.

**Response 200:** HTML page (see [Admin Dashboard](#admin-dashboard) section)

---

### `GET /admin/audit`

Structured audit log viewer with filtering, pagination, and summary statistics.

**Authentication:** Required if `ADMIN_PASSWORD` is set.

**Response 200:** Self-contained HTML page with:
- Stats cards (total events, unique sessions, last 24h, warnings, errors)
- Category filter, severity filter, search input
- Paginated audit log table with severity color badges
- Clickable session token to filter by session
- Total count display

---

### `GET /admin/login`

Login page for admin authentication. Only accessible when `ADMIN_PASSWORD` is set.

- **GET:** Returns the login form HTML.
- **POST:** Submits password for authentication.

**POST body:** `application/x-www-form-urlencoded`

| Field | Type | Required |
|-------|------|----------|
| `password` | string | Yes |

**POST response 302:** Redirects to `/admin` on success, returns login form with error on failure.

**Cookie set on success:**

| Cookie | Value | Max Age | Flags |
|--------|-------|---------|-------|
| `touchmorph_admin` | HMAC-signed session token | 24 hours | `HttpOnly`, `SameSite=Strict` |

---

### `GET /admin/logout`

Clears the admin session cookie and redirects to the login page.

**Response 302:** Redirects to `/admin/login`

---

### `GET /api/devices`

Returns a JSON list of all known devices/sessions.

**Authentication:** Required if `ADMIN_PASSWORD` is set.

**Response 200:**

```json
[
  {
    "token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "device_name": "",
    "ip": "192.168.1.100",
    "paired": true,
    "mode": "touchpad",
    "last_active": 1743123456.789
  },
  {
    "token": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "device_name": "",
    "ip": "192.168.1.101",
    "paired": false,
    "mode": "mouse",
    "last_active": 1743123450.123
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `token` | string | Session UUID (truncated in dashboard UI) |
| `device_name` | string | Device nickname (currently unused) |
| `ip` | string | Client IP address (from `x-forwarded-for` or socket remote address) |
| `paired` | boolean | Whether device completed pairing |
| `mode` | string | Current mode: `"mouse"` or `"touchpad"` |
| `last_active` | number | Unix timestamp of last activity |

---

### `POST /api/kick`

Force-disconnects a device by session token.

**Authentication:** Required if `ADMIN_PASSWORD` is set.

**Request body:**

```json
{
  "token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

| Field | Type | Required |
|-------|------|----------|
| `token` | string | Yes — the session token to disconnect |

**Response 200:**

```json
{
  "ok": true
}
```

**Side effects:**
1. Session deleted from SQLite database.
2. Corresponding WebSocket connection terminated via `sio.disconnect(sid)`.
3. In-memory session state cleaned up.
4. Event logged: `"kicked"`.

---

### `GET /api/logs`

Returns recent event log entries.

**Authentication:** Required if `ADMIN_PASSWORD` is set.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | number | 50 | Maximum number of log entries |

**Response 200:**

```json
[
  {
    "id": 1,
    "token": "a1b2c3d4-...",
    "event": "connect",
    "ts": 1743123400.0
  },
  {
    "id": 2,
    "token": "a1b2c3d4-...",
    "event": "paired",
    "ts": 1743123410.0
  },
  {
    "id": 3,
    "token": "a1b2c3d4-...",
    "event": "touchpad:move",
    "ts": 1743123420.0
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | number | Auto-incrementing log ID |
| `token` | string | Session token (truncated in dashboard UI) |
| `event` | string | Event name (see [Event Log Reference](#event-log-reference)) |
| `ts` | number | Unix timestamp |

---

### `GET /api/audit/logs`

Returns filtered, paginated audit log entries.

**Authentication:** Required if `ADMIN_PASSWORD` is set.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `token` | string | — | Filter by session token |
| `category` | string | — | Filter by category: connection, mouse, touchpad, airmouse, presentation, media, system, gesture, admin, security, general |
| `severity` | string | — | Filter by severity: info, warning, error |
| `search` | string | — | Full-text search in event and detail fields |
| `since` | number | — | Unix timestamp — only entries >= this time |
| `until` | number | — | Unix timestamp — only entries <= this time |
| `limit` | number | 50 | Max entries per page |
| `offset` | number | 0 | Pagination offset |

**Response 200:**

```json
{
  "rows": [
    {
      "id": 1,
      "token": "a1b2...",
      "category": "mouse",
      "event": "mouse:move",
      "detail": "{\"x\":500,\"y\":300}",
      "ip": "192.168.1.100",
      "device_name": "Pixel 7",
      "severity": "info",
      "ts": 1743123400.0
    }
  ],
  "total": 1523
}
```

| Field | Type | Description |
|-------|------|-------------|
| `rows` | array | Array of audit log entry objects |
| `total` | number | Total matching entries (for pagination) |

**Audit log entry fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | number | Auto-incrementing ID |
| `token` | string | Session token |
| `category` | string | Event category |
| `event` | string | Socket.IO event name |
| `detail` | string | JSON string with event payload |
| `ip` | string | Client IP address |
| `device_name` | string | Client device name |
| `severity` | string | info, warning, or error |
| `ts` | number | Unix timestamp |

---

### `GET /api/audit/stats`

Returns summary statistics from the audit logs table.

**Authentication:** Required if `ADMIN_PASSWORD` is set.

**Response 200:**

```json
{
  "total": 15230,
  "unique_sessions": 12,
  "last_24h": 892,
  "by_category": {
    "connection": 450,
    "mouse": 8200,
    "touchpad": 3100,
    "airmouse": 2800,
    "system": 500,
    "admin": 180
  },
  "by_severity": {
    "info": 14800,
    "warning": 380,
    "error": 50
  }
}
```

---

### `GET /api/audit/categories`

Returns distinct category values from the audit logs table.

**Authentication:** Required if `ADMIN_PASSWORD` is set.

**Response 200:**

```json
[
  "connection",
  "mouse",
  "touchpad",
  "airmouse",
  "presentation",
  "media",
  "system",
  "gesture",
  "admin",
  "security",
  "general"
]
```

---

### `GET /setup`

The TouchMorph setup page. Returns an HTML page with email configuration form, log viewer, and dependency status check.

**Authentication:** None

**Response 200:** HTML page with:
- Email SMTP configuration form (Save & Test / Test Only buttons)
- Live log viewer (last 50 events)
- Dependency status check (pyautogui, socket.io client build)

---

### `POST /api/setup/email`

Save email configuration without sending a test.

**Authentication:** None

**Request body:**

```json
{
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_user": "user@gmail.com",
  "smtp_pass": "app-password",
  "smtp_from": "user@gmail.com",
  "smtp_to": "phone@example.com"
}
```

**Response 200:**

```json
{ "ok": true }
```

---

### `POST /api/setup/test-email`

Save email configuration and send a test email.

**Authentication:** None

**Request body:** Same as `/api/setup/email`.

**Response 200:**

```json
{ "ok": true, "message": "Test email sent successfully" }
```

On failure:

```json
{ "ok": false, "error": "Connection refused" }
```

---

### `GET /api/setup/status`

Returns dependency and configuration status.

**Authentication:** None

**Response 200:**

```json
{
  "pyautogui": true,
  "client_built": true,
  "email_configured": false,
  "admin_password_set": true,
  "version": "1.0.0"
}
```

---

### `GET /` (Root)

Serves the TouchMorph client application.

**Behavior:**

- If `client/dist/` exists (client has been built): **200** — serves the React application (`index.html` + static assets from `/assets/`).
- If `client/dist/` does not exist: **200** — serves a setup instruction page telling the user to run `python start.py`.

---

## Event Log Reference

The server logs all significant events to the SQLite `logs` table. These are the possible `event` values:

| Event | When It Occurs |
|-------|---------------|
| `connect` | New session created (first WebSocket connect) |
| `reconnect` | Existing session restored (subsequent connects) |
| `disconnect` | WebSocket disconnected |
| `paired` | Device successfully completed pairing |
| `kicked` | Device was kicked from admin dashboard |
| `mode:mouse` | Mode switched to mouse |
| `mode:touchpad` | Mode switched to touchpad |
| `mode:airmouse` | Mode switched to air mouse |
| `mode:presentation` | Mode switched to presentation |
| `mode:media` | Mode switched to media controller |
| `click:left` | Left click performed |
| `click:right` | Right click performed |
| `double_click` | Double-click performed |
| `scroll` | Scroll event processed |
| `mouse:move` | Mouse move event |
| `mouse:click` | Mouse mode click |
| `mouse:doubleclick` | Mouse mode double-click |
| `mouse:scroll` | Mouse mode scroll |
| `mouse:hold` | Mouse hold (drag start) |
| `mouse:release` | Mouse release (drag end) |
| `mouse:drag` | Mouse drag move |
| `touchpad:move` | Touchpad 1-finger move |
| `touchpad:tap` | Touchpad tap (click) |
| `touchpad:two_finger_scroll` | Touchpad 2-finger scroll |
| `airmouse:move` | Air mouse gyro movement |
| `gesture:start` | Multi-touch gesture start |
| `gesture:move` | Multi-touch gesture move |
| `gesture:end` | Multi-touch gesture end |
| `gesture:n_finger_swipe` | Detected n-finger swipe |
| `gesture:pinch` | Detected pinch gesture |
| `presentation:action` | Presentation control action |
| `media:action` | Media playback control |
| `system:action` | System keyboard shortcut |
| `smartscroll:start` | Smart scroll gesture start |
| `smartscroll:move` | Smart scroll gesture move |
| `smartscroll:end` | Smart scroll gesture end |
| `smartscroll:config` | Smart scroll configuration set |
| `screen:info` | Screen dimensions requested |
| `server:shutdown` | Server shutting down (broadcast) |

---

## Authentication Flow

```mermaid
sequenceDiagram
    participant Browser as Admin Browser
    participant Server as Python Server
    participant Client as Phone Client

    Note over Browser,Client: === ADMIN LOGIN ===
    Browser->>Server: GET /admin
    Server-->>Browser: 302 Redirect to /admin/login

    Browser->>Server: GET /admin/login
    Server-->>Browser: Login form HTML

    Browser->>Server: POST /admin/login (password=secret)
    alt Correct password
        Server-->>Browser: 302 Redirect to /admin
        Server->>Browser: Set-Cookie: touchmorph_admin=HMAC...
    else Wrong password
        Server-->>Browser: 200 OK (login form + error message)
    end

    Browser->>Server: GET /admin (with cookie)
    Server-->>Browser: Admin dashboard HTML

    Browser->>Server: GET /api/devices (with cookie)
    Server-->>Browser: JSON device list

    Browser->>Server: POST /api/kick (with cookie)
    Server->>Client: sio.disconnect(sid)
    Server-->>Browser: { "ok": true }

    Note over Browser,Server: === SESSION EXPIRY ===
    Note over Browser: Cookie expires after 24h
    Note over Browser: Or logout: GET /admin/logout
```

### HMAC Cookie Structure

```
touchmorph_admin = "<random_hex>:<unix_timestamp>:<signature>"
```

| Component | Format | Purpose |
|-----------|--------|---------|
| `random_hex` | 32 hex chars (16 bytes) | Uniqueness — prevents replay of same cookie |
| `unix_timestamp` | Decimal number | Expiry check (24h from creation) |
| `signature` | First 16 chars of HMAC-SHA256 | Integrity — prevents tampering |

**Signature calculation (Python):**

```python
import hmac, hashlib

raw = f"{random_hex}:{timestamp}"
sig = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()[:16]
cookie = f"{raw}:{sig}"
```

---

## Socket.IO Transport Details

### Client Connection

```typescript
// Default connection (same origin)
const socket = io({
  transports: ['websocket', 'polling'],
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
});
```

| Option | Value | Description |
|--------|-------|-------------|
| `transports` | `['websocket', 'polling']` | Prefer WebSocket, fall back to HTTP long-polling |
| `reconnection` | `true` | Auto-reconnect on disconnect |
| `reconnectionAttempts` | `Infinity` | Never stop trying to reconnect |
| `reconnectionDelay` | `1000` | Start with 1s delay |
| `reconnectionDelayMax` | `5000` | Max 5s between attempts |

### Vite Dev Proxy Configuration

```typescript
// vite.config.ts
server: {
  proxy: {
    '/socket.io': {
      target: 'http://localhost:3000',  // Python server
      ws: true,                          // WebSocket support
    },
  },
}
```

During development, the Vite dev server (port 5173) proxies all `/socket.io` traffic to the Python server (port 3000 or fallback from `.port` file).

---

## Error Responses

All errors follow HTTP standard codes:

| Status Code | Meaning | Common Causes |
|-------------|---------|---------------|
| 200 | Success | Request processed |
| 302 | Redirect | Not authenticated, redirecting to login |
| 400 | Bad Request | Missing required fields in request body |
| 403 | Forbidden | Directory listing denied (assets) |
| 404 | Not Found | Unknown route |
| 500 | Internal Error | Server-side exception (logged to console) |

WebSocket errors are communicated via dedicated events (`pair:error`) rather than HTTP status codes.

---

## Complete Event Reference Table

```mermaid
mindmap
  root((TouchMorph Events))
    Connection
      connect
      disconnect
      session:restore
      session:created
      session:restored
      server:shutdown
    Pairing
      pair:request
      pair:code
      pair:verify
      pair:success
      pair:error
    Mode
      mode:switch
      mode:switched
      screen:info
    Mouse Control
      mouse:event[type=move]
      mouse:event[type=click]
      mouse:event[type=doubleclick]
      mouse:event[type=scroll]
      mouse:event[type=hold/drag/release]
      click:left
      click:right
      click:double
      scroll
    Touchpad Control
      touchpad:event[type=move]
      touchpad:event[type=tap]
      touchpad:event[type=two_finger_scroll]
    Air Mouse
      airmouse:move
    Gestures
      gesture:start
      gesture:move
      gesture:end
      gesture:n_finger_swipe
    Presentation
      presentation:action
    Media
      media:action
    System
      system:action
    Smart Scroll
      smartscroll:start
      smartscroll:move
      smartscroll:end
      smartscroll:config
    Heartbeat
      ping
```

### Event Summary Table

| Direction | Event | Payload | Response | Notes |
|-----------|-------|---------|----------|-------|
| C→S | `session:restore` | `{ token? }` | `session:created` or `session:restored` | Sent on every connect |
| S→C | `session:created` | `{ token }` | — | New session |
| S→C | `session:restored` | `{ token, paired, mode, screenW, screenH }` | — | Existing session |
| C→S | `pair:request` | — | `pair:code` | Generates new code |
| S→C | `pair:code` | `{ code }` | — | 6-digit code |
| C→S | `pair:verify` | `{ code }` | `pair:success` or `pair:error` | Validates code |
| S→C | `pair:success` | `{ message }` | — | Pairing OK |
| S→C | `pair:error` | `{ message }` | — | Wrong code |
| C→S | `mode:switch` | `{ mode }` | `mode:switched` | mouse/touchpad/airmouse/presentation/media |
| S→C | `mode:switched` | `{ mode, screenWidth, screenHeight }` | — | Confirms switch + screen dims |
| C→S | `screen:info` | — | `screen:info` | Request screen dimensions |
| S→C | `screen:info` | `{ screenWidth, screenHeight }` | — | Screen dimensions response |
| S→C | `server:shutdown` | `{ message }` | — | Server stopping (broadcast) |
| C→S | `mouse:event` | `{ type, x?, y?, ... }` | — | Mouse move/click/drag/hold/release |
| C→S | `touchpad:event` | `{ type, deltaX?, deltaY? }` | — | Touchpad relative move/tap |
| C→S | `airmouse:move` | `{ alpha?, beta, gamma }` | — | Gyroscope movement |
| C→S | `gesture:start` | `{ touches }` | — | Multi-touch start |
| C→S | `gesture:move` | `{ touches }` | — | Multi-touch move |
| C→S | `gesture:end` | `{ touches }` | — | Multi-touch end |
| C→S | `gesture:n_finger_swipe` | `{ direction, fingerCount }` | — | Detected swipe gesture |
| C→S | `presentation:action` | `{ action }` | — | Slide control (next/prev/start/exit/black/white/first/pointer) |
| C→S | `media:action` | `{ action }` | — | Media keys (play_pause/next/prev/vol_up/vol_down/mute) |
| C→S | `system:action` | `{ action }` | — | System shortcuts (alt_tab/copy/paste/etc.) |
| C→S | `smartscroll:start` | `{ touchId, x, y }` | — | Smart scroll start |
| C→S | `smartscroll:move` | `{ touchId, x, y }` | — | Smart scroll move |
| C→S | `smartscroll:end` | `{ touchId }` | — | Smart scroll end |
| C→S | `smartscroll:config` | `{ sensitivity?, naturalScroll?, decay? }` | — | Config scroll params |
| C→S | `click:left` | — | — | Left mouse click |
| C→S | `click:right` | — | — | Right mouse click |
| C→S | `click:double` | — | — | Double click |
| C→S | `scroll` | `{ deltaX?, deltaY? }` | — | Scroll event |
| C→S | `ping` | — | — | Heartbeat (volatile) |

---

## HTTP Endpoint Reference Table

| Method | Path | Auth Required | Content-Type | Response |
|--------|------|---------------|--------------|----------|
| GET | `/` | No | text/html | React app or setup page |
| GET | `/health` | No | application/json | `{"status":"ok"}` |
| GET | `/admin` | If ADMIN_PASSWORD set | text/html | Admin dashboard HTML |
| GET | `/admin/login` | No | text/html | Login form HTML |
| POST | `/admin/login` | No | form-urlencoded | 302 or login form |
| GET | `/admin/logout` | If ADMIN_PASSWORD set | — | 302 to /admin/login |
| GET | `/admin/audit` | If ADMIN_PASSWORD set | text/html | Audit log viewer HTML |
| GET | `/api/devices` | If ADMIN_PASSWORD set | application/json | Device list JSON |
| POST | `/api/kick` | If ADMIN_PASSWORD set | application/json | `{"ok":true}` |
| GET | `/api/logs` | If ADMIN_PASSWORD set | application/json | Log entries JSON |
| GET | `/api/audit/logs` | If ADMIN_PASSWORD set | application/json | Filtered audit entries |
| GET | `/api/audit/stats` | If ADMIN_PASSWORD set | application/json | Audit summary stats |
| GET | `/api/audit/categories` | If ADMIN_PASSWORD set | application/json | Available categories |
| GET | `/setup` | No | text/html | Setup/email config page |
| POST | `/api/setup/email` | No | application/json | Email config result |
| POST | `/api/setup/test-email` | No | application/json | Test email result |
| GET | `/api/setup/status` | No | application/json | Dependency status |
| GET | `/assets/*` | No | varies | Static client assets |

---

## Payload Schema Definitions

### session:restore

```json
{
  "token": "string (optional) — previously saved UUID session token"
}
```

### session:created (Response)

```json
{
  "token": "string — new UUID v4 session token, e.g., 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'",
  "screenWidth": "number — total screen width in pixels",
  "screenHeight": "number — total screen height in pixels"
}
```

### session:restored (Response)

```json
{
  "token": "string — session token (may differ from requested if server rotated it)",
  "paired": "boolean — whether device was previously paired",
  "mode": "string — 'mouse', 'touchpad', 'airmouse', 'presentation', or 'media'",
  "screenWidth": "number — total screen width in pixels",
  "screenHeight": "number — total screen height in pixels"
}
```

### pair:request

No payload. The server generates a new 6-digit code and invalidates any previous code.

### pair:code (Response)

```json
{
  "code": "string — 6-digit numeric code, e.g., '482917'"
}
```

### pair:verify

```json
{
  "code": "string (required) — the 6-digit code displayed after pair:request"
}
```

### pair:success (Response)

```json
{
  "message": "string — 'Device paired successfully'"
}
```

### pair:error (Response)

```json
{
  "message": "string — 'Invalid pairing code'"
}
```

### mode:switch

```json
{
  "mode": "string (required) — 'mouse', 'touchpad', 'airmouse', 'presentation', or 'media'"
}
```

### mode:switched (Response)

```json
{
  "mode": "string — confirmed mode",
  "screenWidth": "number — total screen width in pixels",
  "screenHeight": "number — total screen height in pixels"
}
```

### mouse:event — Move

```json
{
  "type": "'move'",
  "x": "number — absolute X coordinate (0 to screen width)",
  "y": "number — absolute Y coordinate (0 to screen height)"
}
```

### mouse:event — Click

```json
{
  "type": "'click'",
  "button": "'left' | 'right'"
}
```

### mouse:event — Double Click

```json
{
  "type": "'doubleclick'"
}
```

### mouse:event — Scroll

```json
{
  "type": "'scroll'",
  "deltaX": "number — horizontal scroll delta",
  "deltaY": "number — vertical scroll delta"
}
```

### touchpad:event — Move

```json
{
  "type": "'move'",
  "deltaX": "number — horizontal delta from last position",
  "deltaY": "number — vertical delta from last position",
  "fingerCount": "number (optional) — 1 or 2"
}
```

### touchpad:event — Tap

```json
{
  "type": "'tap'"
}
```

### touchpad:event — Two-Finger Scroll

```json
{
  "type": "'two_finger_scroll'",
  "deltaX": "number — horizontal scroll delta",
  "deltaY": "number — vertical scroll delta",
  "fingerCount": "number — 2"
}
```

### click:left / click:right / click:double

No payload.

### scroll

```json
{
  "deltaX": "number (optional) — horizontal scroll delta, default 0",
  "deltaY": "number (optional) — vertical scroll delta, default 0"
}
```

### mouse:event — Hold / Release / Drag

```json
{
  "type": "'hold'",
  "button": "'left' (optional)"
}
```

```json
{
  "type": "'release'"
}
```

```json
{
  "type": "'drag'",
  "x": "number — absolute X coordinate (0 to screen width)",
  "y": "number — absolute Y coordinate (0 to screen height)"
}
```

### airmouse:move

```json
{
  "alpha": "number (optional) — compass heading in degrees",
  "beta": "number — front-back tilt in degrees",
  "gamma": "number — left-right tilt in degrees"
}
```

### gesture:start / gesture:move / gesture:end

```json
{
  "touches": [
    { "id": "number — unique touch identifier", "x": "number — X coordinate", "y": "number — Y coordinate" }
  ]
}
```

### gesture:n_finger_swipe

```json
{
  "direction": "string — 'up', 'down', 'left', or 'right'",
  "fingerCount": "number — 2, 3, or 4+"
}
```

### presentation:action

```json
{
  "action": "string — 'next', 'prev', 'black', 'white', 'start', 'escape', 'first', or 'pointer'"
}
```

### media:action

```json
{
  "action": "string — 'play_pause', 'next', 'prev', 'vol_up', 'vol_down', or 'mute'"
}
```

### system:action

```json
{
  "action": "string — 'alt_tab', 'task_view', 'show_desktop', 'lock_screen', 'copy', 'paste', 'cut', 'undo', 'redo', 'select_all', 'save', 'find', 'esc', 'enter', or 'fullscreen'"
}
```

### smartscroll:start / smartscroll:move / smartscroll:end

```json
{
  "touchId": "number — unique touch identifier",
  "x": "number (start/move only) — X coordinate",
  "y": "number (start/move only) — Y coordinate"
}
```

### smartscroll:config

```json
{
  "sensitivity": "number (optional) — scroll sensitivity multiplier, default 1.0",
  "naturalScroll": "boolean (optional) — reverse scroll direction, default false",
  "decay": "number (optional) — momentum decay rate 0.0-1.0, default 0.92"
}
```

### screen:info (Request)

No payload.

### screen:info (Response)

```json
{
  "screenWidth": "number — total screen width in pixels",
  "screenHeight": "number — total screen height in pixels"
}
```

### server:shutdown (Response)

```json
{
  "message": "string — 'Server is shutting down'"
}
```

### ping

No payload. Sent as volatile event (not queued if connection congested).

---

## Custom Client Examples

### Python Client

You can write a custom Python client to control TouchMorph:

```python
import socketio

sio = socketio.Client()

@sio.event
def connect():
    print("Connected!")
    sio.emit("pair:verify", {"code": "482917"})

@sio.on("pair:success")
def on_pair(data):
    print("Paired!")
    sio.emit("mouse:event", {"type": "move", "x": 500, "y": 300})
    sio.emit("click:left")

@sio.on("pair:error")
def on_error(data):
    print(f"Pairing failed: {data['message']}")

sio.connect("http://localhost:3000")
sio.wait()
```

### JavaScript Client (Node.js)

```javascript
const { io } = require("socket.io-client");

const socket = io("http://localhost:3000");

socket.on("connect", () => {
  console.log("Connected:", socket.id);

  socket.emit("session:restore", { token: "" });
});

socket.on("session:created", (data) => {
  console.log("New session:", data.token);
  // Save token for later use
});

socket.on("session:restored", (data) => {
  console.log("Restored session, paired:", data.paired);
});

socket.on("pair:code", (data) => {
  console.log("Pairing code:", data.code);
});

// Move mouse and click
function moveMouse(x, y) {
  socket.emit("mouse:event", { type: "move", x, y });
}

function clickLeft() {
  socket.emit("click:left");
}

function clickRight() {
  socket.emit("click:right");
}

// Use
moveMouse(500, 300);
setTimeout(() => clickLeft(), 100);
```

### curl Examples

```bash
# Health check
curl http://localhost:3000/health

# Admin dashboard
curl http://localhost:3000/admin

# Device list (no auth)
curl http://localhost:3000/api/devices

# Admin login
curl -X POST http://localhost:3000/admin/login \
  -d "password=mysecret" \
  -c cookies.txt \
  -L

# Device list (with auth)
curl http://localhost:3000/api/devices -b cookies.txt

# Kick a device
curl -X POST http://localhost:3000/api/kick \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"token": "a1b2c3d4-..."}'

# Event logs
curl http://localhost:3000/api/logs -b cookies.txt

# Audit logs (filtered + paginated)
curl "http://localhost:3000/api/audit/logs?category=mouse&severity=warning&limit=10" -b cookies.txt

# Audit stats summary
curl http://localhost:3000/api/audit/stats -b cookies.txt

# Audit categories
curl http://localhost:3000/api/audit/categories -b cookies.txt

# Admin audit dashboard
curl http://localhost:3000/admin/audit -b cookies.txt

# Setup / email config page
curl http://localhost:3000/setup

# Test email config (no auth needed)
python server/email_service.py --test
```

---

## Socket.IO Configuration Reference

### Server Configuration (`server/main.py`)

```python
sio = socketio.AsyncServer(
    async_mode="aiohttp",
    cors_allowed_origins="*",          # Allow all origins
    cors_credentials=True,             # Allow cookies in CORS
    ping_interval=25,                  # Server ping interval (seconds)
    ping_timeout=60,                   # Timeout before disconnect
    max_http_buffer_size=1000000,      # Max HTTP poll buffer
)
```

### Client Configuration (`client/src/hooks/useSocket.ts`)

```typescript
const socket = io({
  transports: ['websocket', 'polling'],   // Prefer WebSocket
  reconnection: true,                       // Auto-reconnect
  reconnectionAttempts: Infinity,           // Never stop
  reconnectionDelay: 1000,                  // Start with 1s
  reconnectionDelayMax: 5000,               // Max 5s between retries
  timeout: 20000,                           // Connection timeout
  autoConnect: true,                        // Connect on construction
});
```

### Socket.IO Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `transports` | `["polling", "websocket"]` | Transport order (prefer WebSocket) |
| `reconnection` | `true` | Auto-reconnect on disconnect |
| `reconnectionAttempts` | `Infinity` | Max reconnect attempts |
| `reconnectionDelay` | `1000` | Initial reconnect delay (ms) |
| `reconnectionDelayMax` | `5000` | Max reconnect delay (ms) |
| `randomizationFactor` | `0.5` | Randomize delay to prevent thundering herd |
| `timeout` | `20000` | Connection timeout (ms) |
| `autoConnect` | `true` | Connect automatically on construction |
| `withCredentials` | `false` | Send cookies in CORS requests |
| `forceNew` | `false` | Force new connection (skip pool) |

---

## Event Timing and Ordering

### Expected Timing

| Phase | Typical Duration | Notes |
|-------|-----------------|-------|
| TCP connect | 1-5ms | Local network |
| WebSocket upgrade | 5-15ms | Single round-trip |
| session:restore → response | 2-5ms | SQLite lookup |
| pair:request → pair:code | <1ms | In-memory generation |
| pair:verify → pair:success | 2-5ms | SQLite update |
| mouse:event → cursor moves | 3-10ms | WebSocket + pyautogui |

### Race Conditions to Avoid

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server

    Note over C,S: RACE: Double pair:request
    C->>S: pair:request
    S-->>C: pair:code { code: "111111" }
    C->>S: pair:request (user tapped again)
    S-->>C: pair:code { code: "222222" }
    C->>S: pair:verify { code: "111111" }
    Note over S: First code invalidated by second request!
    S-->>C: pair:error { message: "Invalid pairing code" }

    Note over C,S: FIX: Disable button after tap
```

**Best practice:** Disable the "Generate Code" button after tapping it until a code is received or an error occurs.

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server

    Note over C,S: RACE: Event before pairing
    C->>S: mouse:event (sent before pair:success)
    S->>S: _is_active() checks paired status
    Note over S: Device not paired — event ignored
    C->>S: pair:verify { code: "482917" }
    S-->>C: pair:success
    C->>S: mouse:event (now paired — works)

    Note over C,S: Client must wait for pair:success before sending control events
```
