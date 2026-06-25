# Troubleshooting

This document covers common issues, their causes, and how to fix them. If you encounter a problem not listed here, check the server logs (CLI output or `events.log`) for error messages.

## Quick Reference

| Problem | Quick Fix |
|---------|-----------|
| Page won't load on phone | Check WiFi / same network / firewall |
| WebSocket won't connect | Check server is running / correct URL |
| Mouse moves but lags badly | Reduce sensitivity / check network latency |
| Clicks not working | Check server logs / pyautogui permissions |
| Email not sending | Run `python email_service.py --test` |
| Tunnel URL not appearing | Check cloudflared is installed and started |
| CLI shows "Server stopped" | Port in use / check `server.log` |

## Connection Issues

### Phone cannot load the page

**Symptoms:**
- Browser shows "Site cannot be reached", "Connection refused", or timeout
- Page never finishes loading
- White screen with no status bar

**Causes and solutions:**

1. **Different WiFi networks**
   - Ensure phone and laptop are on the same network
   - Check the laptop's IP address with `ipconfig` (Windows) or `ip addr` (Linux/macOS)
   - For local access, use `http://<ip>:5000` (not `https://`)

2. **Firewall blocking port 5000 (Windows)**
   - Verify the firewall rule exists:
     ```powershell
     netsh advfirewall firewall show rule name="Remote Mouse 5000"
     ```
   - If missing, add it:
     ```powershell
     netsh advfirewall firewall add rule name="Remote Mouse 5000" dir=in action=allow protocol=TCP localport=5000
     ```
   - Temporary test: disable the firewall (not recommended for security) and try again

3. **Server not running**
   - Check the terminal window: the server should show "Server starting on port 5000..."
   - If `cli.py` is used, check the CLI output for errors
   - Look for Python traceback errors

4. **Wrong port**
   - If you changed the port in `server.py`, use `http://<ip>:<new-port>`
   - The default is 5000

5. **Phone browser issues**
   - Try Chrome, Edge, or Safari (latest versions)
   - Clear browser cache and reload
   - Disable any ad blockers or VPN on the phone

### WebSocket disconnects or reconnects constantly

**Symptoms:**
- Status bar toggles between "Connected" and "Disconnected"
- "Reconnecting (1)", "Reconnecting (2)", etc. in a loop
- Mouse stops responding intermittently

**Causes and solutions:**

1. **Unstable WiFi**
   - Move closer to the router
   - Reduce interference (microwaves, cordless phones, etc.)
   - Try 5GHz WiFi instead of 2.4GHz

2. **Network congestion**
   - Close bandwidth-heavy applications on the laptop (streaming, downloads)
   - Disconnect other devices from the network

3. **Cloudflare tunnel timeout (remote access)**
   - Free Cloudflare tunnels may drop idle connections
   - The auto-reconnect should recover within 5 seconds
   - If persistent, restart the tunnel

4. **Laptop goes to sleep**
   - Disable sleep when on AC power:
     - Windows: Settings > System > Power & sleep > Never
     - macOS: System Preferences > Energy Saver > Never
     - Linux: `systemctl mask sleep.target`

### Local IP changes every boot

**Solution:** Use a static IP address on your laptop.

**Windows:**
1. Settings > Network & Internet > WiFi > Hardware properties
2. Edit IP assignment > Manual > On
3. Enter an IP outside the DHCP range (e.g., 10.0.0.100 if DHCP is 10.0.0.2–10.0.0.99)
4. Set Subnet prefix length: 24, Gateway: your router's IP, DNS: 8.8.8.8 / 1.1.1.1

**Better solution:** Use the Cloudflare tunnel for remote access — the URL stays the same for the session duration regardless of IP changes.

## Mouse Control Issues

### Cursor does not move

**Symptoms:**
- Status shows "Connected"
- Dragging on touchpad does nothing
- No log entries appear

**Causes and solutions:**

1. **No events reaching the server**
   - Check the CLI output: do you see `> move` entries when you drag?
   - If not, the events are not reaching the server — check WebSocket connection
   - If yes, the issue is with pyautogui

2. **pyautogui permissions (macOS)**
   - macOS requires Accessibility permissions for pyautogui
   - Go to System Preferences > Security & Privacy > Privacy > Accessibility
   - Add Terminal (or your Python interpreter) to the list
   - Restart the server

3. **pyautogui permissions (Linux)**
   - May need to install `python3-xlib` or `python3-tk`
   - On Wayland (instead of X11), pyautogui has limited support — switch to X11
   - Try: `pip install python-xlib`

4. **Multiple displays**
   - pyautogui works across multiple monitors
   - If the cursor moves off-screen, move it back slowly
   - The server sends the screen resolution on connect — verify it matches your setup

### Cursor moves in wrong direction

**Symptoms:**
- Dragging up on phone moves cursor down
- Dragging right moves cursor left

**Solution:**
The touchpad maps touch deltas directly to cursor deltas. If your phone orientation or screen layout causes inverted axes, you can fix it by modifying the JavaScript in `index.html`:

```javascript
// In the touchmove handler, negate dx or dy:
socket.emit('mouse_move', {
  dx: -dx * sensitivity,
  dy: dy * sensitivity  // or -dy to invert both
});
```

### Sensitivity too high or too low

**Solution:** Adjust the sensitivity slider in the Settings panel (gear icon).

- **Too fast:** Set sensitivity to 0.5x or 0.2x
- **Too slow:** Set sensitivity to 2.0x or 3.0x
- The slider adjusts in real time — no need to reload

### Two-finger scroll does not work

**Causes and solutions:**

1. **Not using two fingers**
   - Use exactly two fingers on the touchpad
   - The scroll zone on the right edge is just an indicator — scroll works anywhere

2. **Movement threshold too high**
   - The server requires a minimum scroll delta to trigger
   - Drag more firmly or increase the number of scroll pixels

3. **Scroll direction inverted**
   - This is expected on macOS with "natural scrolling"
   - Modify the scroll handler in `server.py` if needed:
     ```python
     pyautogui.scroll(clicks if dy > 0 else -clicks, _pause=False)
     ```
   - Swap the sign to invert direction

### Drag Mode not working as expected

**Symptoms:**
- Drag mode does not hold the button
- Drag mode moves cursor without clicking

**Solutions:**

1. **Drag Mode behavior:**
   - When Drag Mode is ON, a single-finger drag holds the left mouse button
   - A tap still works as a regular left click
   - Toggle with the center button in the click bar (turns green when active)

2. **The drag movement is faster than normal**
   - This is intentional — drag mode applies a 1.2x multiplier to make selections easier
   - Adjust by editing the multiplier in `index.html`:
     ```javascript
     { dx: dx * sensitivity * 1.2, dy: dy * sensitivity * 1.2 }
     ```

## Media Controls Issues

### Media buttons do nothing

**Symptoms:**
- Pressing Play/Pause has no effect
- No log entries in the CLI

**Causes and solutions:**

1. **No application is playing media**
   - Open a media player (Spotify, VLC, YouTube in browser) first
   - Media keys are system-wide but need an active media session

2. **Media keys not supported on this OS**
   - Windows: Supported natively
   - macOS: Supported, but some apps may require focus
   - Linux: May need additional packages (e.g., `playerctl`)

3. **Wrong key mapping**
   - Check `server.py` line ~160-170 for the key mapping
   - Verify `playpause`, `prevtrack`, etc. match your OS key names

### Volume changes are too large/small

pyautogui's `press('volumeup')` sends a single media key press. The volume change depends on your OS settings:
- Windows: Typically 2% per press
- macOS: Typically 1 notch per press
- Linux: Varies by desktop environment

To send multiple presses, modify the `handle_media` function in `server.py`:

```python
@socketio.on('media')
def handle_media(data):
    action = data.get('action', '')
    key_map = {
        'vol_up': 'volumeup',
        'vol_down': 'volumedown',
        # ...
    }
    key = key_map.get(action)
    if key:
        count = 3 if action in ('vol_up', 'vol_down') else 1  # Send 3 presses
        for _ in range(count):
            pyautogui.press(key, _pause=False)
```

## Email Issues

### Email not sending — test fails

**Symptoms:**
- `python email_service.py --test` fails
- Error: "Missing SMTP configuration"
- Error: "Authentication failed"

**Causes and solutions:**

1. **Missing .env file**
   - Create it: `cp .env.example .env`
   - Fill in your SMTP credentials

2. **Wrong SMTP credentials**
   - Gmail: Use an App Password, not your regular password
   - Other providers: Check your account settings
   - Common mistake: trailing spaces in `.env` values

3. **Port blocked (465/587)**
   - Some networks (corporate, public WiFi) block SMTP ports
   - Try connecting from a different network (e.g., phone hotspot)
   - Check if your antivirus/firewall is blocking outbound SMTP

4. **Gmail "App Password" required**
   - App Passwords only work with 2-Step Verification enabled
   - Generate at: https://myaccount.google.com/apppasswords
   - Use the 16-character password (no spaces) in `.env`

5. **SMTP_TO_EMAIL not set**
   - When running `--test`, the default recipient is used
   - Either set `SMTP_TO_EMAIL` in `.env` or pass a recipient

### Email sends but phone does not receive it

**Solutions:**
1. Check spam/junk folder
2. Carrier SMS gateways may have delays (30 seconds to 5 minutes)
3. Some carriers block messages from unknown senders
4. Try sending to a regular email address (e.g., Gmail) first

## Tunnel Issues

### Cloudflare tunnel fails to start

**Symptoms:**
- `cloudflared tunnel --url http://localhost:5000` errors
- Tunnel process exits immediately
- `.tunnel_url` is empty or missing

**Causes and solutions:**

1. **cloudflared not installed**
   - Download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
   - Verify with: `cloudflared version`

2. **Port 5000 not accessible**
   - Ensure the server is running: `python server.py` in a separate terminal
   - Test: `curl http://localhost:5000` should return the HTML

3. **Network restrictions**
   - Some networks block tunneling tools
   - Try using a different network or using a VPN

4. **cloudflared update required**
   - Update: `cloudflared update` or download the latest version

### Tunnel URL changes every minute

This is normal for free Cloudflare tunnels. The URL changes:
- Every time you restart cloudflared
- After tunnel idle timeout (typically several hours)

The auto-reconnect handles URL changes — the frontend polls `/api/tunnel-url` to get the latest URL.

## CLI Issues

### CLI won't start ("Python not found")

**Solution:** Add Python to your PATH:
- Windows: Re-run the Python installer and check "Add Python to PATH"
- Verify: `python --version` in a new terminal

### CLI shows "Server stopped" immediately

**Causes and solutions:**

1. **Port 5000 already in use**
   - Find the process: `netstat -ano | findstr :5000`
   - Kill it: `taskkill /PID <pid> /F`
   - Or change the port in `server.py`

2. **Python dependency missing**
   - Run: `pip install -r requirements.txt`
   - Check for errors during installation

3. **Syntax error in server.py**
   - Run: `python -m py_compile server.py`
   - Fix any errors reported

### CLI log output is garbled or missing colors

**Solution:** colorama may not be installed or initialized:
```bash
pip install colorama
```

On Windows 10+ with the new terminal, colorama is optional. On older Windows or Linux/macOS without proper terminal support, install colorama for colored output.

## Performance Issues

### High latency

**Symptoms:**
- Noticeable delay between phone touch and cursor movement
- Cursor jumps or stutters

**Solutions:**
1. **Local access:** Ensure both devices are on the same WiFi network
2. **5GHz WiFi:** Less interference and lower latency than 2.4GHz
3. **Reduce network load:** Close streaming, downloads, video calls on the laptop
4. **Lower sensitivity:** High sensitivity amplifies small delays
5. **Cloudflare tunnel:** Will always add 50-200ms vs. local access

### Cursor jitter

**Symptoms:**
- Cursor vibrates or shakes when not moving
- Small unintentional movements registered

**Solutions:**
1. **Increase dead zone:** In `index.html`, increase the movement threshold:
   ```javascript
   if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {  // Changed from > 1 to > 3
   ```
2. **Lower sensitivity:** Reduces the effect of small finger movements
3. **Clean phone screen:** Oily or wet screens can cause erratic touch readings

## Platform-Specific Issues

### macOS: pyautogui not working

**Step-by-step fix:**
1. Open System Settings > Privacy & Security > Accessibility
2. Click the lock icon (bottom-left) and enter your password
3. Click the + button and add your terminal application (e.g., Terminal.app or iTerm2)
4. Also add `Python.app` if visible (usually in `/System/Library/Frameworks/Python.framework/`)
5. Restart the Remote Mouse server
6. Test again

If it still does not work, run the server from the Python launcher app instead of Terminal.

### Linux: Wayland vs X11

pyautogui requires X11. If you are using Wayland (default on many modern Linux distros):

**Option 1:** Switch to X11 on the login screen (gear icon before entering password)

**Option 2:** Use `xdotool` as an alternative:
```python
import subprocess
subprocess.run(['xdotool', 'mousemove_relative', '--', str(dx), str(dy)])
```

**Option 3:** Install `python3-xlib` for partial Wayland support.

### Windows: Antivirus blocking

Some antivirus software may block pyautogui or Python's network access. Add exceptions for:
- `python.exe` (or `python3.exe`)
- Port 5000 (TCP inbound/outbound)

### Phone browser compatibility

| Browser | Status | Notes |
|---------|--------|-------|
| Chrome (Android) | ✅ Fully supported | Best experience |
| Edge (Android) | ✅ Fully supported | Same engine as Chrome |
| Samsung Internet | ✅ Supported | May have minor CSS differences |
| Safari (iOS) | ✅ Supported | Some haptic feedback limitations |
| Firefox (Android) | ✅ Supported | Slightly different touch behavior |

**Important for iOS:** Safari on iOS may require the page to be opened from a secure context (HTTPS). If using local HTTP, it should still work, but some features (clipboard API, vibration) may be unavailable.

### iOS: No haptic feedback

`navigator.vibrate()` is not supported on iOS (all browsers on iOS use Safari's WebKit engine, which does not implement the Vibration API). This is normal — clicks still work, they just do not vibrate.

## Error Messages Reference

| Error Message | Meaning | Fix |
|---------------|---------|-----|
| `[Errno 10048] Address already in use` | Port 5000 is already used by another process | Kill the process or change port |
| `pyautogui.PyAutoGUIException` | pyautogui operation failed (macOS permissions, etc.) | Grant permissions or check OS compatibility |
| `smtplib.SMTPAuthenticationError` | SMTP login failed | Check username and password |
| `smtplib.SMTPServerDisconnected` | SMTP server closed connection | Check SMTP host and port |
| `socket.gaierror` | DNS resolution failed | Check network connectivity |
| `requests.exceptions.ConnectionError` | Cannot connect to server | Ensure server is running and reachable |
| `OSError: [WinError 10061]` | Connection actively refused | Server is not running on that port |
