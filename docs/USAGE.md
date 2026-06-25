# Usage Guide

This document covers everything you can do with Remote Mouse — from basic cursor control to advanced workflows.

## Table of Contents

1. [Launching the Application](#launching-the-application)
2. [The Interface](#the-interface)
3. [Touchpad Controls](#touchpad-controls)
4. [Click Bar](#click-bar)
5. [Drag Mode](#drag-mode)
6. [Media Controls](#media-controls)
7. [Link Page](#link-page)
8. [Sensitivity Adjustment](#sensitivity-adjustment)
9. [CLI Control Panel](#cli-control-panel)
10. [Tips and Tricks](#tips-and-tricks)

## Launching the Application

### Daily Use

The recommended way to start Remote Mouse is the CLI control panel:

```bash
python cli.py
```

This gives you a live log of all events and a command interface. The server starts automatically and runs in the background.

### Quick Launch (Windows)

Create a shortcut to `cli.py` or use `start.bat` if you created one. Double-click to start.

### With Tunnel

If you need remote access (phone on cellular data, different network):

**Windows:**
```powershell
.\scripts\start.ps1
```

**Linux/macOS:**
```bash
./scripts/start.sh
```

## The Interface

The phone interface has three main tabs, accessible from the bottom navigation bar:

| Tab | Icon | Purpose |
|-----|------|---------|
| Touchpad | 🖱 | Cursor movement, clicking, scrolling |
| Media | 🎵 | Media playback controls |
| Link | 🔗 | View/share the tunnel URL |

There is also a Settings button (⚙) that opens the sensitivity slider.

### Status Bar

At the top of the screen, the status bar shows:
- **Connection indicator** — a green dot when the WebSocket is connected, gray when disconnected
- **Status text** — "Connected", "Disconnected", or "Reconnecting (attempt #)"
- **IP address** — the laptop's local network IP

If the status shows "Disconnected" or "Reconnecting", check:
1. The server is running on your laptop
2. Your phone and laptop are on the same network (for local access)
3. The tunnel is still active (for remote access)
4. The URL is correct

## Touchpad Controls

The touchpad is the main interface. It occupies the upper portion of the screen and responds to touch gestures.

### Single Finger Drag (Move Cursor)

Place one finger on the touchpad and drag. The cursor on your laptop moves in the same direction and proportional to your finger movement.

- Small movements = precise cursor control
- Fast movements = large cursor sweeps
- The sensitivity slider affects how much the cursor moves per millimeter of finger travel

### Single Finger Tap (Left Click)

Tap (touch and lift quickly) on the touchpad with one finger. This performs a left mouse click at the current cursor position.

- The tap threshold is 400ms — if you hold longer than 400ms before lifting, it does not register as a click
- If you move your finger more than ~1 pixel during the touch, it becomes a drag operation instead of a click
- Haptic feedback (vibration) on supported phones confirms the click

### Two Finger Drag (Scroll)

Place two fingers on the touchpad and drag up or down. This performs a scroll action:

- **Drag up** — scrolls down (content moves up)
- **Drag down** — scrolls up (content moves down)
- The scroll speed is proportional to the drag speed
- Two-finger horizontal scroll is not currently supported

### Touch Zones

The touchpad area includes a vertical scroll zone on the right edge (marked with ↕). You can also scroll anywhere on the touchpad with two fingers — the dedicated zone is primarily a visual indicator.

## Click Bar

The click bar sits below the touchpad and provides three buttons:

### Left Click

The green "Left" button performs a left mouse click. Use this when you need a precise click without the tap gesture.

### Right Click

The red "Right" button performs a right mouse click. This opens context menus in most applications (desktop right-click menu, browser context menu, etc.).

### Drag Mode Toggle

The center button (⊞/⊟) toggles Drag Mode on and off:

- **Drag Mode OFF (⊞):** Normal touchpad behavior — drag moves the cursor, tap clicks
- **Drag Mode ON (⊟, highlighted green):** Drag holds the left mouse button down — use this for:
  - Selecting text or files (click and drag to create a selection rectangle)
  - Moving windows (drag the title bar)
  - Resizing windows (drag the edges/corners)
  - Drag-and-drop operations

When Drag Mode is active, a single finger drag performs a left-button drag (mouseDown + move + mouseUp on release). A tap still performs a regular click.

## Media Controls

The Media tab provides buttons for controlling media playback on your laptop. These work with any application that supports media keys (media keys are system-level on most operating systems).

### Playback Controls

| Button | Action | Key Sent |
|--------|--------|----------|
| ▶ (big center) | Play/Pause toggle | `playpause` |
| ⏮ (left) | Previous track | `prevtrack` |
| ⏭ (right) | Next track | `nexttrack` |

### Volume Controls

| Button | Action | Key Sent |
|--------|--------|----------|
| 🔉 (Volume Down) | Decrease volume | `volumedown` |
| 🔊 (Mute) | Toggle mute | `volumemute` |
| 🔊 (Volume Up) | Increase volume | `volumeup` |

### Notes on Media Keys

- These are system-wide media keys, equivalent to physical media keys on a keyboard
- They work with: Spotify, Apple Music, VLC, YouTube (in Chrome/Edge), Windows Media Player, and most media applications
- On macOS, some applications may need to be in focus
- The mute button toggles — pressing it again unmutes

## Link Page

The Link tab shows the current tunnel URL and provides ways to share it with your phone.

### Viewing the URL

The current tunnel URL is displayed in a card. If a Cloudflare tunnel is active, the URL appears in green. If no tunnel is active, it shows "Waiting for tunnel..."

### Copying the URL

Tap "Copy to clipboard" to copy the URL. On most phones, a confirmation toast appears. You can then paste the URL into any app (messenger, email, notes, etc.).

### Emailing the URL

If SMTP is configured on the laptop:

1. Enter your email address (or SMS gateway address) in the input field
2. Tap "Send to my phone"
3. A confirmation message appears: "✓ Sent! Check your phone."
4. Check your phone's email or SMS inbox for the link

If SMTP is not configured, you will see an error: "No tunnel URL available" or "Failed to send email."

### Fallback: REST API

The Link page also fetches the tunnel URL from `GET /api/tunnel-url` as a fallback when the WebSocket is not yet connected. This means the URL appears on the page even if the WebSocket handshake is still in progress.

## Sensitivity Adjustment

### Opening the Sensitivity Panel

Tap the gear icon (⚙) in the bottom navigation bar. A panel slides up from the bottom.

### Adjusting Sensitivity

Drag the slider to adjust the mouse speed multiplier:

| Value | Effect |
|-------|--------|
| 0.2x | Very slow — precise control, good for detailed work |
| 0.5x | Slow — comfortable for most tasks |
| 1.0x | Default — balanced speed |
| 2.0x | Fast — move across screen with small gestures |
| 3.0x | Very fast — minimal finger movement needed |

### Closing the Panel

Tap "Done" in the top-right corner of the panel, or tap the gear icon again.

### Persistence

The sensitivity value is **not persisted** between page loads. When you reload the page or reconnect, it resets to 1.0x. This is by design — you can set it per-session based on your current activity.

## CLI Control Panel

The CLI (`cli.py`) provides a terminal-based interface for managing the server.

### Starting

```bash
python cli.py
```

### Commands

| Command | Aliases | Description |
|---------|---------|-------------|
| `help` | `h` | Show available commands |
| `status` | `st` | Show server state, local IP, tunnel URL |
| `log` | `l` | Show last 50 action log entries |
| `clear` | `cls` | Clear the terminal screen |
| `exit` | `q`, `quit` | Stop the server and exit |

### Live Log Display

While the server is running, all events are displayed in real time with color coding:

| Color | Prefix | Event Type |
|-------|--------|------------|
| Green | `>` | Mouse/keyboard actions (move, click, scroll, etc.) |
| Cyan | `*` | System messages (server start, client connect/disconnect, email sent) |
| Gray | `[timestamp]` | All other log lines |

### Log Output Examples

```
  [19:30:22] * Server starting on port 5000...
  [19:30:22] * Local:  http://10.0.0.5:5000
  [19:30:22] * Tunnel: https://abcdefgh.trycloudflare.com
  [19:31:05] * Client connected
  [19:31:12] > move   (+0045, -0023)
  [19:31:12] > move   (+0012, -0005)
  [19:31:14] > click  left
  [19:31:18] > scroll (+00120)
  [19:31:22] > media  play_pause
  [19:32:01] * Client disconnected
```

### Stopping

Type `q`, `quit`, or `exit` to stop the server and CLI. You can also press `Ctrl+C` or `Ctrl+D`.

## Tips and Tricks

### Presentations

1. Open your presentation (PowerPoint, Google Slides, PDF) on the laptop
2. Open Remote Mouse on your phone
3. Use the touchpad to advance slides by tapping (left click) or scrolling down
4. Use the Media tab to play/pause embedded videos

### Movie Watching

1. Open your movie player (VLC, MPC-HC, browser) on the laptop
2. Open Remote Mouse on your phone
3. Use Media controls for play/pause, volume, and skipping
4. Use the touchpad to seek by clicking on the player's progress bar

### File Management

1. Open File Explorer (Windows) or Finder (macOS)
2. Enable Drag Mode on Remote Mouse
3. Drag files to move them between folders
4. Use right-click for context menus (rename, copy, delete)

### Web Browsing

1. Open Chrome or Edge on the laptop
2. Use the touchpad to move the cursor
3. Tap to follow links
4. Use two-finger scroll for long pages
5. For keyboard shortcuts (Ctrl+T, Ctrl+W, etc.), these can be added via the `key` WebSocket event

### Accessibility

- If you have difficulty using a physical mouse, Remote Mouse lets you use touch gestures instead
- The sensitivity slider helps if you need very slow or very fast cursor movement
- Large touch targets (buttons are 52-80px) are easy to tap accurately

### Power Users

- Use `cli.py` to watch live events and understand what the server is doing
- The `status` command shows both local and tunnel URLs at a glance
- The `log` command shows the last 50 events, useful for debugging

### Battery Saving

- Keep the phone plugged in during extended use
- Close other apps to reduce network contention
- Lower screen brightness
