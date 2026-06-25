import os
import json
import logging
import asyncio
import signal

import socketio
from aiohttp import web

from config import Config
from socket_handler import TouchMorphSocket
from email_service import EmailService
from session_store import (
    cleanup_stale_sessions,
    trim_logs,
    vacuum_db,
    get_logs,
    list_sessions,
    query_audit_logs,
    count_audit_logs,
    get_audit_stats,
    audit_log,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("touchmorph")

config = Config()
email_service = EmailService(config)
touchmorph = TouchMorphSocket()

sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="aiohttp")
app = web.Application()
sio.attach(app)

# ─── Socket.IO event binding ──────────────────────────────────────────────

@sio.event
async def connect(sid, environ):
    await touchmorph.on_connect(sid, environ)

@sio.event
async def disconnect(sid):
    await touchmorph.on_disconnect(sid)

@sio.event
async def session_restore(sid, data):
    await touchmorph.on_session_restore(sid, data, sio)

@sio.event
async def pair_request(sid):
    await touchmorph.on_pair_request(sid, sio)

@sio.event
async def pair_verify(sid, data):
    await touchmorph.on_pair_verify(sid, data, sio)

@sio.event
async def mode_switch(sid, data):
    await touchmorph.on_mode_switch(sid, data, sio)

@sio.event
async def click(sid, button):
    await touchmorph.on_click(sid, button)

@sio.event
async def click_left(sid):
    await touchmorph.on_click(sid, "left")

@sio.event
async def click_right(sid):
    await touchmorph.on_click(sid, "right")

@sio.event
async def click_double(sid):
    await touchmorph.on_double_click(sid)

@sio.event
async def double_click(sid):
    await touchmorph.on_double_click(sid)

@sio.event
async def scroll(sid, data):
    await touchmorph.on_scroll(sid, data)

@sio.event
async def mouse_event(sid, data):
    await touchmorph.on_mouse_event(sid, data)

@sio.event
async def mouse_hold(sid):
    await touchmorph.on_mouse_hold(sid)

@sio.event
async def mouse_release(sid):
    await touchmorph.on_mouse_release(sid)

@sio.event
async def mouse_drag(sid, data):
    await touchmorph.on_mouse_drag(sid, data)

@sio.event
async def touchpad_event(sid, data):
    await touchmorph.on_touchpad_event(sid, data)

@sio.event
async def smart_scroll_start(sid):
    await touchmorph.on_smart_scroll_start(sid)

@sio.event
async def smart_scroll_move(sid, data):
    await touchmorph.on_smart_scroll_move(sid, data)

@sio.event
async def smart_scroll_end(sid):
    await touchmorph.on_smart_scroll_end(sid, sio)

@sio.event
async def smart_scroll_config(sid, data):
    await touchmorph.on_smart_scroll_config(sid, data)

@sio.event
async def gesture_start(sid, data):
    await touchmorph.on_gesture_start(sid, data)

@sio.event
async def gesture_move(sid, data):
    await touchmorph.on_gesture_move(sid, data, sio)

@sio.event
async def gesture_end(sid, data):
    await touchmorph.on_gesture_end(sid, data, sio)

@sio.event
async def gesture_n_finger_swipe(sid, data):
    await touchmorph.on_gesture_n_finger_swipe(sid, data, sio)

@sio.event
async def airmouse_move(sid, data):
    await touchmorph.on_airmouse_move(sid, data)

@sio.event
async def airmouse_click(sid, data):
    await touchmorph.on_airmouse_click(sid, data)

@sio.event
async def screen_info(sid):
    await touchmorph.on_screen_info(sid, sio)

@sio.event
async def presentation_action(sid, data):
    await touchmorph.on_presentation_action(sid, data)

@sio.event
async def media_action(sid, data):
    await touchmorph.on_media_action(sid, data)

@sio.event
async def system_action(sid, data):
    await touchmorph.on_system_action(sid, data)

# ─── HTTP routes ──────────────────────────────────────────────────────────

async def handle_index(request):
    return web.FileResponse(config.get_client_path() / "index.html")


async def handle_admin(request):
    resp = _check_admin(request)
    if resp:
        return resp
    return web.FileResponse(config.get_client_path() / "index.html")


async def handle_admin_api(request):
    resp = _check_admin(request)
    if resp:
        return resp
    devices = await touchmorph.get_devices()
    return web.json_response({"devices": devices})


async def handle_kick(request):
    resp = _check_admin(request)
    if resp:
        return resp
    data = await request.json()
    device_token = data.get("token", "")
    await touchmorph.kick_device(device_token, sio)
    return web.json_response({"status": "ok"})


async def handle_setup(request):
    return web.FileResponse(config.get_client_path() / "index.html")


async def handle_setup_api_email(request):
    data = await request.json()
    smtp_host = data.get("smtp_host", "").strip()
    smtp_port = data.get("smtp_port", 587)
    smtp_user = data.get("smtp_user", "").strip()
    smtp_pass = data.get("smtp_pass", "").strip()
    from_email = data.get("from_email", "").strip()
    to_email = data.get("to_email", "").strip()

    if not all([smtp_host, smtp_port, from_email, to_email]):
        return web.json_response({"error": "Missing required fields"}, status=400)

    config.set_email_config(smtp_host, smtp_port, smtp_user, smtp_pass, from_email, to_email)
    return web.json_response({"status": "ok", "message": "Email configuration saved"})


async def handle_setup_api_test_email(request):
    try:
        result = email_service.send_email(
            subject="TouchMorph Test",
            body="Your email configuration is working correctly.",
        )
        return web.json_response({"status": "ok" if result else "error", "message": "Email sent" if result else "Failed to send"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)})


async def handle_setup_api_status(request):
    deps = {
        "pyautogui": True,
        "python-socketio": True,
        "aiohttp": True,
    }
    try:
        import pyautogui
    except ImportError:
        deps["pyautogui"] = False
    email_configured = bool(config.smtp_host)
    devices = await touchmorph.get_devices()
    logs = get_logs(50)

    return web.json_response({
        "version": config.VERSION,
        "dependencies": deps,
        "email_configured": email_configured,
        "connected_devices": len(devices),
        "recent_logs": logs,
    })


async def handle_logs(request):
    resp = _check_admin(request)
    if resp:
        return resp
    limit = int(request.query.get("limit", 50))
    logs = get_logs(limit)
    return web.json_response({"logs": logs})

# ─── Audit API ────────────────────────────────────────────────────────────

async def handle_audit_logs(request):
    resp = _check_admin(request)
    if resp:
        return resp
    limit = int(request.query.get("limit", 50))
    offset = int(request.query.get("offset", 0))
    token = request.query.get("token")
    category = request.query.get("category")
    severity = request.query.get("severity")
    search = request.query.get("search")
    since = request.query.get("since")
    until = request.query.get("until")
    if since:
        try:
            since = float(since)
        except (TypeError, ValueError):
            since = None
    if until:
        try:
            until = float(until)
        except (TypeError, ValueError):
            until = None
    entries = query_audit_logs(
        token=token, category=category, severity=severity,
        search=search, limit=limit, offset=offset,
        since=since, until=until,
    )
    total = count_audit_logs(
        token=token, category=category, severity=severity,
        search=search, since=since, until=until,
    )
    return web.json_response({
        "entries": entries,
        "total": total,
        "limit": limit,
        "offset": offset,
    })


async def handle_audit_stats(request):
    resp = _check_admin(request)
    if resp:
        return resp
    stats = get_audit_stats()
    return web.json_response(stats)


async def handle_audit_categories(request):
    resp = _check_admin(request)
    if resp:
        return resp
    from session_store import CATEGORIES
    return web.json_response({"categories": list(CATEGORIES)})


# ─── Admin audit HTML page ────────────────────────────────────────────────

ADMIN_AUDIT_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TouchMorph — Audit Logs</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f1117; color: #e1e4e8; padding: 24px; }
h1 { font-size: 22px; margin-bottom: 20px; color: #f0f6fc; }
.stats { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
.stat-card { background: #1c1e26; border: 1px solid #2d3039; border-radius: 8px; padding: 14px 20px; min-width: 120px; }
.stat-card .num { font-size: 28px; font-weight: 600; color: #58a6ff; }
.stat-card .label { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: .5px; }
.filters { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; align-items: center; }
.filters select, .filters input, .filters button {
    background: #1c1e26; border: 1px solid #2d3039; border-radius: 6px; padding: 8px 12px; color: #e1e4e8; font-size: 13px; outline: none;
}
.filters select:focus, .filters input:focus { border-color: #58a6ff; }
.filters button {
    background: #238636; border-color: #2ea043; cursor: pointer; font-weight: 500;
}
.filters button:hover { background: #2ea043; }
.filters .clear { background: #21262d; border-color: #30363d; }
.filters .clear:hover { background: #30363d; }
table { width: 100%; border-collapse: collapse; background: #1c1e26; border-radius: 8px; overflow: hidden; border: 1px solid #2d3039; }
th { text-align: left; padding: 10px 14px; font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: .5px; border-bottom: 1px solid #2d3039; background: #16181f; }
td { padding: 8px 14px; border-bottom: 1px solid #22242c; font-size: 13px; vertical-align: top; }
tr:hover td { background: #22242c; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; }
.badge-info { background: #0c2d6b; color: #58a6ff; }
.badge-warning { background: #3d2e00; color: #d29922; }
.badge-error { background: #3d1114; color: #f85149; }
.badge-category { background: #1c2d3d; color: #79c0ff; }
.token { font-family: ui-monospace, monospace; font-size: 11px; color: #8b949e; cursor: pointer; }
.token:hover { color: #58a6ff; }
.detail { font-size: 11px; color: #8b949e; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ts { font-size: 11px; color: #6e7681; white-space: nowrap; }
.pagination { display: flex; gap: 8px; align-items: center; margin-top: 16px; }
.pagination button { background: #21262d; border: 1px solid #30363d; border-radius: 6px; padding: 6px 14px; color: #e1e4e8; cursor: pointer; font-size: 13px; }
.pagination button:disabled { opacity: .4; cursor: default; }
.pagination button:hover:not(:disabled) { background: #30363d; }
.pagination .info { font-size: 13px; color: #8b949e; }
.total-row { font-size: 13px; color: #8b949e; margin-bottom: 8px; }
tr td:first-child { font-size: 11px; color: #6e7681; }
</style>
</head>
<body>
<h1>Audit Logs</h1>
<div class="stats" id="stats"></div>
<div class="filters">
    <select id="filter-category"><option value="">All categories</option></select>
    <select id="filter-severity">
        <option value="">All severities</option>
        <option value="info">Info</option>
        <option value="warning">Warning</option>
        <option value="error">Error</option>
    </select>
    <input id="filter-search" placeholder="Search events..." size="20">
    <button id="btn-apply">Apply</button>
    <button id="btn-clear" class="clear">Clear</button>
</div>
<div class="total-row" id="total-label"></div>
<table><thead><tr>
    <th>ID</th><th>Time</th><th>Category</th><th>Event</th><th>Detail</th><th>Session</th><th>IP</th><th>Sev</th>
</tr></thead><tbody id="log-body"></tbody></table>
<div class="pagination" id="pagination"></div>
<script>
const LIMIT = 50;
let offset = 0;
let total = 0;
async function loadStats() {
    const r = await fetch('/api/audit/stats');
    const s = await r.json();
    document.getElementById('stats').innerHTML = `
        <div class="stat-card"><div class="num">${s.total}</div><div class="label">Total Events</div></div>
        <div class="stat-card"><div class="num">${s.unique_sessions}</div><div class="label">Sessions</div></div>
        <div class="stat-card"><div class="num">${s.last_24h}</div><div class="label">Last 24h</div></div>
        <div class="stat-card"><div class="num">${s.by_severity.warning || 0}</div><div class="label">Warnings</div></div>
        <div class="stat-card"><div class="num">${s.by_severity.error || 0}</div><div class="label">Errors</div></div>
    `;
}
async function loadCategories() {
    const r = await fetch('/api/audit/categories');
    const d = await r.json();
    const sel = document.getElementById('filter-category');
    d.categories.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c;
        opt.textContent = c;
        sel.appendChild(opt);
    });
}
function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}
function truncateToken(t) {
    if (t && t.length > 8) return t.slice(0, 8) + '...';
    return t || '-';
}
function formatTime(ts) {
    const d = new Date(ts * 1000);
    return d.toLocaleString();
}
async function loadLogs() {
    const params = new URLSearchParams({ limit: LIMIT, offset });
    const cat = document.getElementById('filter-category').value;
    const sev = document.getElementById('filter-severity').value;
    const search = document.getElementById('filter-search').value.trim();
    if (cat) params.set('category', cat);
    if (sev) params.set('severity', sev);
    if (search) params.set('search', search);
    const r = await fetch(`/api/audit/logs?${params}`);
    const d = await r.json();
    total = d.total;
    offset = d.offset;
    document.getElementById('total-label').textContent = `${total} total entries`;
    const tbody = document.getElementById('log-body');
    tbody.innerHTML = d.entries.map(e => {
        const sevClass = e.severity === 'error' ? 'badge-error' : e.severity === 'warning' ? 'badge-warning' : 'badge-info';
        let detail = e.detail || '';
        if (detail.length > 60) detail = detail.slice(0, 60) + '...';
        return `<tr>
            <td>${e.id}</td>
            <td class="ts">${formatTime(e.ts)}</td>
            <td><span class="badge badge-category">${escapeHtml(e.category)}</span></td>
            <td><strong>${escapeHtml(e.event)}</strong></td>
            <td class="detail" title="${escapeHtml(e.detail || '')}">${escapeHtml(detail)}</td>
            <td><span class="token" onclick="setFilterToken('${escapeHtml(e.token || '')}')">${truncateToken(e.token)}</span></td>
            <td style="font-size:11px;color:#6e7681">${escapeHtml(e.ip || '-')}</td>
            <td><span class="badge ${sevClass}">${e.severity}</span></td>
        </tr>`;
    }).join('');
    renderPagination();
}
function setFilterToken(tok) {
    document.getElementById('filter-search').value = tok;
    offset = 0;
    loadLogs();
}
function renderPagination() {
    const nav = document.getElementById('pagination');
    const page = Math.floor(offset / LIMIT) + 1;
    const pages = Math.ceil(total / LIMIT) || 1;
    nav.innerHTML = `
        <button onclick="goPage(0)" ${offset <= 0 ? 'disabled' : ''}>First</button>
        <button onclick="goPage(${offset - LIMIT})" ${offset <= 0 ? 'disabled' : ''}>Prev</button>
        <span class="info">Page ${page} of ${pages}</span>
        <button onclick="goPage(${offset + LIMIT})" ${offset + LIMIT >= total ? 'disabled' : ''}>Next</button>
        <button onclick="goPage(${Math.floor((pages - 1)) * LIMIT})" ${offset + LIMIT >= total ? 'disabled' : ''}>Last</button>
    `;
}
function goPage(newOffset) {
    if (newOffset < 0) newOffset = 0;
    if (newOffset >= total) newOffset = Math.max(0, Math.floor((total - 1) / LIMIT) * LIMIT);
    offset = newOffset;
    loadLogs();
}
document.getElementById('btn-apply').addEventListener('click', () => { offset = 0; loadLogs(); });
document.getElementById('btn-clear').addEventListener('click', () => {
    document.getElementById('filter-category').value = '';
    document.getElementById('filter-severity').value = '';
    document.getElementById('filter-search').value = '';
    offset = 0;
    loadLogs();
});
loadStats();
loadCategories();
loadLogs();
</script>
</body>
</html>"""


async def handle_admin_audit(request):
    resp = _check_admin(request)
    if resp:
        return resp
    return web.Response(text=ADMIN_AUDIT_HTML, content_type="text/html")


# ─── Auth helper ──────────────────────────────────────────────────────────

def _check_admin(request):
    expected = config.get_admin_token()
    if not expected:
        return web.json_response({"error": "Admin not configured"}, status=403)
    token = request.cookies.get("admin_token", "")
    if token != expected:
        return web.json_response({"error": "Unauthorized"}, status=403)
    return None


# ─── Router ───────────────────────────────────────────────────────────────

app.router.add_get("/", handle_index)
app.router.add_get("/admin", handle_admin)
app.router.add_get("/setup", handle_setup)
app.router.add_get("/api/admin/devices", handle_admin_api)
app.router.add_post("/api/admin/kick", handle_kick)
app.router.add_post("/api/setup/email", handle_setup_api_email)
app.router.add_post("/api/setup/test-email", handle_setup_api_test_email)
app.router.add_get("/api/setup/status", handle_setup_api_status)
app.router.add_get("/api/logs", handle_logs)
app.router.add_get("/api/audit/logs", handle_audit_logs)
app.router.add_get("/api/audit/stats", handle_audit_stats)
app.router.add_get("/api/audit/categories", handle_audit_categories)
app.router.add_get("/admin/audit", handle_admin_audit)

client_static = config.get_client_path()
if client_static.exists():
    app.router.add_static("/assets/", path=client_static / "assets")

# ─── Cleanup task ─────────────────────────────────────────────────────────

async def cleanup_loop():
    vacuum_counter = 0
    while True:
        await asyncio.sleep(3600)
        try:
            stale = cleanup_stale_sessions()
            trimmed = trim_logs()
            if stale or trimmed:
                vacuum_counter += 1
                if vacuum_counter >= 5:
                    vacuum_db()
                    vacuum_counter = 0
        except Exception as e:
            logger.exception("Cleanup task error: %s", e)


# ─── Graceful shutdown ────────────────────────────────────────────────────

async def shutdown_handler(app):
    logger.info("Shutting down — notifying connected clients...")
    try:
        async for sid in sio.manager.get_participants("/", None):
            try:
                await sio.emit("server:shutdown", {"message": "Server is shutting down"}, to=sid)
            except Exception:
                pass
    except (NotImplementedError, AttributeError):
        logger.warning("get_participants not available — skipping shutdown broadcast")
    except Exception as e:
        logger.warning("Error during shutdown notification: %s", e)
    logger.info("Shutdown complete.")


async def on_startup(app):
    app["cleanup_task"] = asyncio.create_task(cleanup_loop())


async def on_cleanup(app):
    task = app.get("cleanup_task")
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    await shutdown_handler(app)


app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)


# ─── Main ─────────────────────────────────────────────────────────────────

def main():
    host = config.host
    port = config.port
    logger.info(f"TouchMorph v{config.VERSION} starting on {host}:{port}")

    from session_store import DB_PATH
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Client directory: {client_static}")

    web.run_app(app, host=host, port=port, print=lambda _: None)


if __name__ == "__main__":
    main()
