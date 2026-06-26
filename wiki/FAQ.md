# Frequently Asked Questions

## General

### What makes this different from other remote mouse apps?

No phone installation. Zero. The phone just opens a URL in the browser. No app store, no APK download, no permissions to grant. The server is three Python files with no database and no authentication — minimal attack surface.

### Does it work over the internet?

Yes, through a Cloudflare tunnel (cloudflared). The setup wizard automatically starts the tunnel and emails the URL to your phone. Expect 50–200ms latency vs 5–15ms on local WiFi.

### Does it work on iPhone?

Yes. Safari (iOS) is fully supported. The only limitation is no haptic feedback — iOS WebKit doesn't implement `navigator.vibrate()`.

### Is authentication needed?

No. The project is designed for personal use on trusted networks. Tunnel URLs are random (64-bit entropy) and change on restart.

## Technical

### Why does the page load so fast?

The Socket.IO client library (49 KB) is served from the laptop's `/static/` directory, not from a CDN. On phone hotspot connections, CDN downloads take 3+ minutes due to carrier routing. Local serving makes it instant.

### Why does the server use eventlet?

Flask-SocketIO needs `eventlet` or `gevent` for native WebSocket support. Without it, the server falls back to HTTP long-polling which adds latency. `eventlet.monkey_patch()` is required at line 1 of `server.py`.

### Can I change the port?

Yes. Edit `socketio.run(app, host='0.0.0.0', port=5000)` in `server.py`. Update the Windows Firewall rule and cloudflared tunnel command if you change it.

### How do I reset the click counter?

Click counters are not implemented yet (planned for v3.2.0 in the version plan). All settings are currently session-only.

## Troubleshooting

### The cursor doesn't move but it says "Connected"

Check the CLI output for `> move` entries. If present, the issue is with pyautogui (macOS permissions, Linux Wayland, etc.). If absent, the WebSocket events aren't reaching the server.

### Two-finger scroll doesn't work

This was a known bug in v5.0.0 — `prev1.y` was used instead of `prev1.lastY`. Fixed in v5.0.1. Ensure you have the latest version of `frontend/index.html`.

### Email not sending

Run `python src/email_service.py --test` to isolate the issue. Common causes: missing `.env` file, wrong App Password (Gmail), port 587 blocked by network.

### The tunnel URL changes every session

This is expected for free Cloudflare tunnels. The URL changes on every restart and after idle timeout (~2 hours). The frontend auto-refreshes via `/api/tunnel-url`.

## Contributing

### How do I add a new feature?

1. Check if it's in the version plan (`version_control.md`)
2. Follow the spec ordering — each version builds on the prior
3. Update both `docs/` (HTML) and `wiki/` (Markdown)
4. Run the compilation check

### Why is the frontend a single HTML file?

Simplicity. No build step, no npm, no webpack, no vite. Edit the file and reload — that's the workflow. The trade-off is larger file size (~17 KB), which is still negligible compared to the 49 KB socket.io library.

### Can I add a framework like React or Vue?

Please don't. The project intentionally avoids build tools to keep the barrier to entry as low as possible. Vanilla JS keeps the frontend accessible to any developer without a node_modules directory.
