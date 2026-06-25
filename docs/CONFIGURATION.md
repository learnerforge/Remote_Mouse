# Configuration Reference

This document describes all configuration options for Remote Mouse — environment variables, file paths, server settings, and how to customize behavior.

## Environment Variables (.env)

The `.env` file configures SMTP email delivery. Create it by copying `.env.example`:

```bash
cp .env.example .env
```

### SMTP Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SMTP_HOST` | Yes | — | SMTP server hostname (e.g., `smtp.gmail.com`) |
| `SMTP_PORT` | No | `587` | SMTP server port (`587` for STARTTLS, `465` for SSL) |
| `SMTP_USERNAME` | Yes | — | SMTP authentication username (usually your email) |
| `SMTP_PASSWORD` | Yes | — | SMTP authentication password or App Password |
| `SMTP_FROM_EMAIL` | No | same as `SMTP_USERNAME` | The From: address in sent emails |
| `SMTP_TO_EMAIL` | Yes* | — | Default recipient (your phone email or SMS gateway) |

\* `SMTP_TO_EMAIL` is required when using `email_service.py` from the command line, but when the server sends via the web form (`/api/send-url`), the recipient is provided in the POST request.

### Example: Gmail

```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your.name@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SMTP_FROM_EMAIL=your.name@gmail.com
SMTP_TO_EMAIL=5551234567@vtext.com
```

### Example: Outlook

```ini
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=your.name@outlook.com
SMTP_PASSWORD=your-password
SMTP_FROM_EMAIL=your.name@outlook.com
SMTP_TO_EMAIL=your.name@outlook.com
```

### Example: Yahoo Mail

```ini
SMTP_HOST=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USERNAME=your.name@yahoo.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your.name@yahoo.com
SMTP_TO_EMAIL=your.name@yahoo.com
```

## Server Configuration (server.py)

The server has no external configuration file — all settings are defined directly in `server.py`. To customize, edit the file.

### Port

```python
socketio.run(app, host='0.0.0.0', port=5000, ...)
```

Change `port=5000` to any available port (e.g., `port=8080`). If you change the port, also update:
- The cloudflared tunnel command: `cloudflared tunnel --url http://localhost:<new-port>`
- The startup scripts (start.ps1 and start.sh)
- The Windows Firewall rule if port changed

### Bind Address

```python
socketio.run(app, host='0.0.0.0', port=5000, ...)
```

- `0.0.0.0` — listen on all network interfaces (accessible from other devices)
- `127.0.0.1` — listen only on localhost (not accessible from other devices)

### Secret Key

```python
app.config['SECRET_KEY'] = os.urandom(24).hex()
```

The secret key is randomly generated on each server start. It is used by Flask-Session for signing session cookies. Since the server is stateless and there is no authentication, this is not critical for security — it is required by Flask-SocketIO internally.

### pyautogui Settings

```python
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0
```

| Setting | Default | Current | Effect |
|---------|---------|---------|--------|
| `FAILSAFE` | `True` | `False` | When True, moving the mouse to a corner raises an exception. Disabled to prevent accidental crashes. |
| `PAUSE` | `0.1` | `0` | Built-in pause after each pyautogui call. Set to 0 for zero-latency responsiveness. |

## File Paths

### Log File

```python
EVENT_LOG_FILE = 'events.log'
```

All server events are appended to this file. It is created automatically in the project root. The CLI's `log` command reads from this file.

**Note:** The log file grows indefinitely. Consider adding log rotation for long-running sessions.

### Tunnel URL File

```python
TUNNEL_URL_FILE = '.tunnel_url'
```

The startup scripts write the Cloudflare tunnel URL to this file. The server reads it to expose via the API and WebSocket.

**Format:** A single line containing the full HTTPS URL.
**Example content:** `https://abcdefgh123456.trycloudflare.com`

### Static Files Directory

```python
# In server.py:
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)
```

The `static/` directory contains the local Socket.IO client library (`socket.io.min.js`). You can add other static assets here (icons, images, etc.) and they will be served at `/static/<filename>`.

### index.html

The frontend file must be at the project root. The server serves it at `GET /`:

```python
@app.route('/')
def index():
    return send_file('index.html')
```

## Frontend Configuration (index.html)

All frontend configuration is inline in `index.html`. Key configurable values:

### Socket.IO Connection Options

```javascript
const socket = io({
  transports: ['websocket', 'polling'],
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
});
```

| Option | Current Value | Description |
|--------|---------------|-------------|
| `transports` | `['websocket', 'polling']` | Prefer WebSocket, fallback to HTTP long-polling |
| `reconnection` | `true` | Auto-reconnect on disconnect |
| `reconnectionAttempts` | `Infinity` | Never give up reconnecting |
| `reconnectionDelay` | `1000` | Initial delay before first reconnection (ms) |
| `reconnectionDelayMax` | `5000` | Maximum delay between reconnection attempts (ms) |

### Sensitivity Range

```html
<input type="range" id="sens-slider" min="0.2" max="3.0" step="0.1" value="1.0">
```

| Attribute | Current Value | Description |
|-----------|---------------|-------------|
| `min` | `0.2` | Minimum sensitivity (0.2x = very slow) |
| `max` | `3.0` | Maximum sensitivity (3.0x = very fast) |
| `step` | `0.1` | Granularity of adjustment |
| `value` | `1.0` | Default sensitivity |

### Tap Threshold

```javascript
if (e.changedTouches.length === 1 && !touchMoved && Date.now() - touchStartTime < 400) {
```

The `400` is the maximum duration in milliseconds for a touch to be considered a tap (click). Adjust to make taps more or less forgiving:
- Lower values (e.g., `200`): Only very quick touches register as clicks
- Higher values (e.g., `600`): Slower touches also register as clicks

### Movement Threshold

```javascript
if (Math.abs(dx) > 1 || Math.abs(dy) > 1) {
```

The `1` is the minimum pixel movement required to trigger a mouse move event. Increase to reduce jitter (at the cost of precision).

### Drag Mode Multiplier

```javascript
if (dragMode) {
  socket.emit('mouse_move', { dx: dx * sensitivity * 1.2, dy: dy * sensitivity * 1.2 });
}
```

The `1.2` multiplier in drag mode makes cursor movement slightly faster during drag operations. This compensates for the fact that dragging across the screen typically requires larger cursor movements.

## Startup Scripts

### start.ps1 (Windows)

The PowerShell script has these configurable values at the top:

```powershell
$ProjectRoot = Split-Path -Parent $PSScriptRoot
```

All other settings are derived automatically. No manual configuration needed for basic use.

### start.sh (Linux/macOS)

```bash
PROJECT_ROOT=$(pwd)
```

Same — fully automatic.

## Windows Firewall Rule

If you change the port, update the firewall rule:

```powershell
# Delete old rule
netsh advfirewall firewall delete rule name="Remote Mouse 5000"

# Add new rule with new port
netsh advfirewall firewall add rule name="Remote Mouse 5000" dir=in action=allow protocol=TCP localport=8080
```

## Cloudflare Tunnel

### Custom Domain (Advanced)

By default, cloudflared generates a random `*.trycloudflare.com` URL. To use a custom domain:

1. Install and authenticate cloudflared: `cloudflared tunnel login`
2. Create a tunnel with a name: `cloudflared tunnel create my-mouse`
3. Configure DNS to point your domain to the tunnel
4. Run: `cloudflared tunnel run my-mouse`

This is beyond the scope of basic setup — see the [Cloudflare Tunnel documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) for details.

### Tunnel Logging

cloudflared writes logs to `tunnel.log` in the project root when started by the launcher scripts. Check this file if the tunnel fails to start.

## Events Log

The `events.log` file is auto-created in the project root. It contains all server events with timestamps:

```
[19:30:22] * Server starting on port 5000...
[19:30:22] * Local:  http://10.0.0.5:5000
[19:31:05] * Client connected
[19:31:12] > move   (+0045, -0023)
```

The CLI's `log` command reads the last 50 lines from this file. The file grows without rotation — for long sessions, consider periodically clearing it or adding log rotation.

## Troubleshooting Configuration

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Email not sending | SMTP credentials wrong | Test with `python email_service.py --test` |
| Tunnel URL not showing | cloudflared not started | Check `.tunnel_url` exists and has content |
| Server won't bind to port | Port in use | Change port in `server.py` |
| Phone can't connect (local) | Firewall blocking | Check Windows Firewall rule |
| Phone can't connect (remote) | Tunnel not running | Check cloudflared is installed and started |
| JavaScript errors on phone | Old browser | Use Chrome, Edge, or Safari (latest versions) |
