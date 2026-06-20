import asyncio
import socketio
import hmac
import hashlib
import secrets
import time
from pathlib import Path
from aiohttp import web

from config import HOST, PORT, ADMIN_PASSWORD, ADMIN_SECRET
from socket_handler import TouchMorphSocket

sio = socketio.AsyncServer(async_mode="aiohttp", cors_allowed_origins="*")
app = web.Application()
sio.attach(app)

handler = TouchMorphSocket()


@sio.event
async def connect(sid, environ, auth):
    await handler.on_connect(sid, environ)


@sio.event
async def disconnect(sid):
    await handler.on_disconnect(sid)


@sio.on("session:restore")
async def on_session_restore(sid, data):
    await handler.on_session_restore(sid, data, sio)


@sio.on("pair:request")
async def on_pair_request(sid):
    await handler.on_pair_request(sid, sio)


@sio.on("pair:verify")
async def on_pair_verify(sid, data):
    await handler.on_pair_verify(sid, data, sio)


@sio.on("mode:switch")
async def on_mode_switch(sid, data):
    await handler.on_mode_switch(sid, data, sio)


@sio.on("click:left")
async def on_click_left(sid):
    await handler.on_click(sid, "left")


@sio.on("click:right")
async def on_click_right(sid):
    await handler.on_click(sid, "right")


@sio.on("click:double")
async def on_click_double(sid):
    await handler.on_double_click(sid)


@sio.on("scroll")
async def on_scroll(sid, data):
    await handler.on_scroll(sid, data)


@sio.on("mouse:event")
async def on_mouse_event(sid, data):
    await handler.on_mouse_event(sid, data)


@sio.on("touchpad:event")
async def on_touchpad_event(sid, data):
    await handler.on_touchpad_event(sid, data)


# --- HTTP Endpoints ---

async def health(request):
    return web.json_response({"status": "ok"})


async def get_devices(request):
    devices = await handler.get_devices()
    return web.json_response(devices)


async def admin_dashboard(request):
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TouchMorph - Dashboard</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; }
h1 { color: #818cf8; margin-bottom: 1.5rem; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 0.75rem 1rem; border-bottom: 1px solid #1e293b; }
th { color: #64748b; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }
td { font-size: 0.875rem; }
.badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge-green { background: #166534; color: #86efac; }
.badge-yellow { background: #854d0e; color: #fde047; }
.badge-gray { background: #334155; color: #cbd5e1; }
.btn-kick { background: #991b1b; color: #fca5a5; border: none; padding: 0.25rem 0.75rem; border-radius: 6px; cursor: pointer; font-size: 0.75rem; }
.btn-kick:hover { background: #b91c1c; }
.refresh { margin-bottom: 1rem; color: #64748b; font-size: 0.875rem; }
#log { margin-top: 2rem; }
#log pre { background: #1e293b; padding: 1rem; border-radius: 8px; font-size: 0.75rem; max-height: 300px; overflow-y: auto; color: #94a3b8; }
</style>
</head>
<body>
<h1>TouchMorph Dashboard</h1>
<p class="refresh">Devices: <span id="count">0</span> &middot; <a href="#" onclick="load(); return false;" style="color:#818cf8">Refresh</a> &middot; <a href="/admin/logout" style="color:#fca5a5">Logout</a></p>
<table>
<thead><tr><th>Token</th><th>IP</th><th>Status</th><th>Mode</th><th>Last Active</th><th></th></tr></thead>
<tbody id="devices"></tbody>
</table>
<div id="log">
<h2 style="color:#818cf8;font-size:1rem;margin-bottom:0.5rem">Event Log</h2>
<pre id="log-content">Loading...</pre>
</div>
<script>
async function load() {
  const [devRes, logRes] = await Promise.all([
    fetch('/api/devices'),
    fetch('/api/logs')
  ]);
  const devices = await devRes.json();
  const logs = await logRes.json();
  document.getElementById('count').textContent = devices.length;
  document.getElementById('devices').innerHTML = devices.map(d => {
    const time = d.last_active ? new Date(d.last_active * 1000).toLocaleTimeString() : '-';
    const status = d.paired ? '<span class="badge badge-green">Paired</span>' : '<span class="badge badge-yellow">Pending</span>';
    return `<tr><td style="font-family:monospace;font-size:0.75rem">${d.token.slice(0,8)}...</td><td>${d.ip || '-'}</td><td>${status}</td><td><span class="badge badge-gray">${d.mode}</span></td><td>${time}</td><td><button class="btn-kick" onclick="kick('${d.token}')">Kick</button></td></tr>`;
  }).join('');
  document.getElementById('log-content').textContent = logs.map(l => `[${new Date(l.ts * 1000).toLocaleTimeString()}] ${l.token.slice(0,8)}... ${l.event}`).join('\\n');
}
async function kick(token) {
  await fetch('/api/kick', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({token}) });
  load();
}
load();
setInterval(load, 3000);
</script>
</body>
</html>"""
    return web.Response(text=html, content_type="text/html")


async def api_kick(request):
    data = await request.json()
    token = data.get("token", "")
    await handler.kick_device(token, sio)
    return web.json_response({"ok": True})


async def api_logs(request):
    from session_store import get_logs
    return web.json_response(get_logs(limit=50))


# --- Admin Auth Helpers ---

def _admin_session_id() -> str:
    raw = f"{secrets.token_hex(16)}:{time.time()}"
    sig = hmac.new(ADMIN_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{raw}:{sig}"


def _check_admin(request) -> bool:
    if not ADMIN_PASSWORD:
        return True  # auth disabled
    cookie = request.cookies.get("touchmorph_admin", "")
    if not cookie:
        return False
    parts = cookie.rsplit(":", 1)
    if len(parts) != 2:
        return False
    raw, sig = parts
    expected = hmac.new(ADMIN_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(sig, expected):
        return False
    ts = float(raw.split(":")[1])
    return (time.time() - ts) < 86400  # 24h expiry


async def admin_login(request):
    error = ""
    if request.method == "POST":
        data = await request.post()
        pwd = data.get("password", "")
        if pwd == ADMIN_PASSWORD:
            resp = web.HTTPFound("/admin")
            resp.set_cookie("touchmorph_admin", _admin_session_id(),
                            max_age=86400, httponly=True, samesite="Strict",
                            secure=False)
            raise resp
        error = "Wrong password"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TouchMorph - Admin Login</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:system-ui,sans-serif; background:#0f172a; color:#e2e8f0; display:flex; align-items:center; justify-content:center; min-height:100vh; }}
form {{ background:#1e293b; padding:2rem; border-radius:16px; width:320px; }}
h1 {{ color:#818cf8; font-size:1.25rem; margin-bottom:1.5rem; text-align:center; }}
input {{ width:100%; padding:0.75rem; border-radius:8px; border:1px solid #334155; background:#0f172a; color:#e2e8f0; font-size:1rem; outline:none; margin-bottom:1rem; }}
input:focus {{ border-color:#818cf8; }}
button {{ width:100%; padding:0.75rem; border:none; border-radius:8px; background:#818cf8; color:#fff; font-size:1rem; cursor:pointer; }}
button:hover {{ background:#6366f1; }}
.error {{ color:#fca5a5; text-align:center; margin-top:0.75rem; font-size:0.875rem; }}
</style></head>
<body>
<form method="post">
<h1>TouchMorph Admin</h1>
<input type="password" name="password" placeholder="Admin password" autofocus required>
<button type="submit">Login</button>
{f'<p class="error">{error}</p>' if error else ''}
</form>
</body>
</html>"""
    return web.Response(text=html, content_type="text/html")


async def admin_logout(request):
    resp = web.HTTPFound("/admin/login")
    resp.del_cookie("touchmorph_admin")
    raise resp


async def auth_middleware(app, handler):
    async def middleware(request):
        path = request.path
        if path in ("/admin/login",) or path.startswith(("/health", "/socket.io")):
            return await handler(request)
        if path.startswith(("/admin", "/api/devices", "/api/kick", "/api/logs")):
            if not _check_admin(request):
                raise web.HTTPFound("/admin/login")
        return await handler(request)
    return middleware


app.middlewares.append(auth_middleware)

app.router.add_get("/health", health)
app.router.add_get("/api/devices", get_devices)
app.router.add_post("/api/kick", api_kick)
app.router.add_get("/api/logs", api_logs)
app.router.add_get("/admin", admin_dashboard)
app.router.add_route("*", "/admin/login", admin_login)
app.router.add_get("/admin/logout", admin_logout)

# --- Serve built client app (production mode) ---

CLIENT_DIST = Path(__file__).resolve().parent.parent / "client" / "dist"

if CLIENT_DIST.is_dir():
    app.router.add_static("/assets", path=str(CLIENT_DIST / "assets"))

    async def serve_client(request):
        index = CLIENT_DIST / "index.html"
        if index.is_file():
            return web.Response(text=index.read_text(encoding="utf-8"),
                                content_type="text/html")
        raise web.HTTPNotFound()

    app.router.add_get("/", serve_client)
else:

    async def serve_setup_page(request):
        html = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TouchMorph</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:1rem}
.card{background:#1e293b;border-radius:16px;padding:2rem;max-width:420px;text-align:center}
h1{color:#818cf8;font-size:1.5rem;margin-bottom:1rem}
p{color:#94a3b8;font-size:0.9rem;line-height:1.5;margin-bottom:1rem}
code{background:#0f172a;color:#a5b4fc;padding:0.25rem 0.5rem;border-radius:6px;font-size:0.85rem}
.step{text-align:left;margin-bottom:0.75rem;padding:0.75rem;background:#0f172a;border-radius:8px;font-size:0.85rem}
.step b{color:#e2e8f0}
.step span{color:#64748b}
a{color:#818cf8}
</style></head>
<body>
<div class="card">
<h1>TouchMorph</h1>
<p>Browser-based remote mouse &amp; touchpad</p>
<div class="step">
<b>1.</b> <span>Run in terminal:</span><br>
<code>python start.py</code>
</div>
<div class="step">
<b>2.</b> <span>Open this page from your phone:</span><br>
<code id="url">http://<LAN-IP>:<PORT>/</code>
</div>
<div class="step">
<b>3.</b> <span>Pair and control your PC remotely.</span>
</div>
<p style="font-size:0.8rem;color:#64748b">
<a href="/admin">Admin Dashboard</a>
</p>
</div>
</body>
</html>"""
        return web.Response(text=html, content_type="text/html")

    app.router.add_get("/", serve_setup_page)


def _get_lan_ip() -> str:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("10.254.254.254", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return HOST


if __name__ == "__main__":
    port_file = Path(__file__).resolve().parent.parent / ".port"

    async def main():
        runner = web.AppRunner(app)
        await runner.setup()

        actual_port = PORT
        for attempt in range(10):
            try:
                site = web.TCPSite(runner, HOST, actual_port)
                await site.start()
                break
            except OSError:
                if attempt < 9:
                    print(f"[TouchMorph] Port {actual_port} in use, trying {actual_port + 1} ...")
                    actual_port += 1
                    continue
                print("[TouchMorph] Could not find an available port after 10 attempts.")
                await runner.cleanup()
                raise SystemExit(1)

        port_file.write_text(str(actual_port))

        lan_ip = _get_lan_ip()
        print(f"[TouchMorph] Server running on {HOST}:{actual_port}")
        print(f"[TouchMorph] Dashboard: http://localhost:{actual_port}/admin")
        print(f"[TouchMorph] Connect from another device: http://{lan_ip}:{actual_port}")

        if not CLIENT_DIST.is_dir():
            print()
            print("  ⚠  Client app not built. Run one of these:")
            print(f"     python start.py      # builds + starts in one command")
            print(f"     cd {CLIENT_DIST.parent} && npm install && npm run build")
            print(f"     Then restart the server.")
            print()

        await asyncio.Event().wait()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[TouchMorph] Shutting down ...")
