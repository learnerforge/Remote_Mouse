# WebSocket Protocol

This document describes the WebSocket protocol used between the phone browser and the Python server. Events are sent via Socket.IO, which provides a convenient abstraction over raw WebSocket with built-in reconnection, fallback to HTTP long-polling, and event routing.

## Transport

- **Primary:** WebSocket
- **Fallback:** HTTP long-polling (Socket.IO handles this automatically)
- **Library:** Socket.IO (client: socket.io 4.x, server: Flask-SocketIO 5.x)
- **Connection URL:** Same as the page URL (e.g., `http://laptop:5000` or `https://tunnel.trycloudflare.com`)

The client connects with:

```javascript
const socket = io({
  transports: ['websocket', 'polling'],
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
});
```

## Event Reference

### Server-to-Client Events

These events are sent from the server to the client.

#### `screen_info`

Sent when a client connects. Provides screen dimensions and connection URLs.

```json
{
  "width": 1920,
  "height": 1080,
  "ip": "10.0.0.5",
  "tunnel_url": "https://abcdefgh.trycloudflare.com"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `width` | int | Screen width in pixels |
| `height` | int | Screen height in pixels |
| `ip` | string | Local IP address of the laptop |
| `tunnel_url` | string | Cloudflare tunnel URL (empty string if no tunnel) |

#### `tunnel_url`

Sent in response to `request_tunnel_url`. Provides the current tunnel URL.

```json
{
  "url": "https://abcdefgh.trycloudflare.com"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `url` | string | Current tunnel URL (empty if no tunnel active) |

### Client-to-Server Events

These events are sent from the phone browser to the server.

#### `mouse_move`

Sent when the user drags a finger on the touchpad.

```json
{
  "dx": 45,
  "dy": -23
}
```

| Field | Type | Description |
|-------|------|-------------|
| `dx` | int | Delta X in pixels (positive = right, negative = left) |
| `dy` | int | Delta Y in pixels (positive = down, negative = up) |

**Server action:** `pyautogui.moveRel(int(dx), int(dy), _pause=False)`

**Notes:**
- The server receives the delta already scaled by the sensitivity multiplier (client-side scaling)
- Delta values should be small (typically 1-50 pixels) for smooth movement
- The server uses `_pause=False` to skip pyautogui's built-in delay

#### `mouse_down`

Sent when a mouse button is pressed (currently not used by the frontend, available for future use).

```json
{
  "button": "left"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `button` | string | `"left"` or `"right"` |

**Server action:** `pyautogui.mouseDown(button='left', _pause=False)`

#### `mouse_up`

Sent when a mouse button is released.

```json
{
  "button": "left"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `button` | string | `"left"` or `"right"` |

**Server action:** `pyautogui.mouseUp(button='left', _pause=False)`

#### `click`

Sent when the user taps the touchpad or presses a click button.

```json
{
  "button": "left"
}
```

```json
{
  "button": "right"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `button` | string | `"left"` or `"right"` |

**Server action:** `pyautogui.click(button='left', _pause=False)`

**Notes:**
- Sent on touchpad tap (if touch duration < 400ms and no significant movement)
- Sent on Left/Right button press in the click bar
- The frontend also triggers haptic feedback (`navigator.vibrate(10)`) on click

#### `double_click`

Sent for a double-click action.

```json
{}
```

No payload needed.

**Server action:** `pyautogui.doubleClick(_pause=False)`

**Note:** Not currently bound to any frontend UI element, but available for use.

#### `scroll`

Sent when the user performs a two-finger scroll gesture.

```json
{
  "dy": 120
}
```

| Field | Type | Description |
|-------|------|-------------|
| `dy` | int | Scroll delta (positive = scroll down, negative = scroll up) |

**Server action:**

```python
clicks = max(1, abs(int(dy / 20)))
pyautogui.scroll(-clicks if dy > 0 else clicks, _pause=False)
```

**Notes:**
- The server converts pixel deltas to "clicks" (notches) by dividing by 20
- A minimum of 1 click is always sent
- Positive dy (finger moving up on screen) scrolls content down (scrolling toward the user)

#### `media`

Sent when the user presses a media control button.

```json
{
  "action": "play_pause"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `action` | string | One of: `play_pause`, `next`, `prev`, `vol_up`, `vol_down`, `mute` |

**Action-to-key mapping:**

| action | Key sent |
|--------|----------|
| `play_pause` | `playpause` |
| `next` | `nexttrack` |
| `prev` | `prevtrack` |
| `vol_up` | `volumeup` |
| `vol_down` | `volumedown` |
| `mute` | `volumemute` |

**Server action:** `pyautogui.press(key, _pause=False)`

**Notes:**
- These are system-wide media keys, not application-specific
- They work on Windows, macOS, and most Linux desktop environments
- The key names follow pyautogui's key naming convention

#### `key`

Sent for keyboard shortcuts and special keys.

```json
{
  "action": "alt_tab"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `action` | string | One of: `alt_tab`, `win_d`, `win_tab`, `win_l`, `esc`, `enter`, `space` |

**Action-to-key mapping:**

| action | Keys | pyautogui call |
|--------|------|----------------|
| `alt_tab` | `('alt', 'tab')` | `hotkey('alt', 'tab')` |
| `win_d` | `('win', 'd')` | `hotkey('win', 'd')` |
| `win_tab` | `('win', 'tab')` | `hotkey('win', 'tab')` |
| `win_l` | `('win', 'l')` | `hotkey('win', 'l')` |
| `esc` | `('esc',)` | `press('esc')` |
| `enter` | `('enter',)` | `press('enter')` |
| `space` | `('space',)` | `press('space')` |

**Server action:**

```python
if len(keys) == 1:
    pyautogui.press(keys[0], _pause=False)
else:
    pyautogui.hotkey(*keys, _pause=False)
```

**Notes:**
- Single-key actions use `press()`. Multi-key combinations use `hotkey()`.
- The `hotkey()` function presses each key in sequence and releases in reverse order, which is the correct behavior for keyboard shortcuts.
- These are not currently bound to any frontend UI element but can be added easily.

#### `request_tunnel_url`

Sent by the client to request the current tunnel URL. No payload.

```json
{}
```

**Server response:** Emits `tunnel_url` event with the current URL.

**Frontend usage:**

```javascript
socket.emit('request_tunnel_url');
```

This is sent automatically on connection to populate the Link page.

## REST API Endpoints

In addition to WebSocket events, the server provides two REST endpoints.

### GET /api/tunnel-url

Returns the current tunnel URL and local IP address.

**Response:**

```json
{
  "url": "https://abcdefgh.trycloudflare.com",
  "local_ip": "10.0.0.5"
}
```

**Frontend usage:** Used as a fallback when the WebSocket is not yet connected.

```javascript
fetch('/api/tunnel-url')
  .then(r => r.json())
  .then(data => {
    if (data.url) updateTunnelUrl(data.url);
  });
```

### POST /api/send-url

Sends the tunnel URL to a specified email address via SMTP.

**Request:**

```json
{
  "email": "user@example.com"
}
```

**Success response (200):**

```json
{
  "success": true,
  "message": "Tunnel URL sent to user@example.com"
}
```

**Error responses:**

```json
// 400 - Invalid email
{ "error": "Invalid email address" }

// 400 - No tunnel
{ "error": "No tunnel URL available" }

// 500 - SMTP failure
{ "error": "Failed to send email: connection refused" }
```

## Error Handling

### Client-Side Reconnection

The Socket.IO client is configured with infinite reconnection attempts:

```javascript
const socket = io({
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 1000,      // Start with 1 second
  reconnectionDelayMax: 5000,   // Cap at 5 seconds
});
```

This means:
- On disconnect, the client waits 1 second before the first reconnection attempt
- Each subsequent attempt increases the delay up to 5 seconds (exponential backoff)
- The reconnection counter is shown in the status bar: "Reconnecting (3)..."
- Reconnection continues indefinitely until the page is closed or the server responds

### Server-Side Logging

All events are logged to stdout and `events.log` with timestamps:

```
[19:31:12] > move   (+0045, -0023)
[19:31:14] > click  left
[19:31:18] > scroll (+00120)
```

## Extending the Protocol

To add a new event:

1. **Client side (`index.html`):** Call `socket.emit('event_name', payload)` where needed
2. **Server side (`server.py`):** Add a `@socketio.on('event_name')` handler
3. **Documentation:** Add the event to this document

The payload can be any JSON-serializable object. The server handler can call any pyautogui function, execute shell commands, or perform any other action.

Example — adding a screenshot trigger:

```python
@socketio.on('screenshot')
def handle_screenshot():
    import pyautogui
    img = pyautogui.screenshot()
    img.save(f'screenshot_{datetime.now():%Y%m%d_%H%M%S}.png')
    log_msg(f"> screenshot saved")
```
