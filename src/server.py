import eventlet
eventlet.monkey_patch()

import os
import re
import subprocess
import socket as sock_lib
import tempfile
import threading
import time
import atexit
import platform
import secrets
import functools
from datetime import datetime
import logging
from collections import deque, defaultdict
from flask import Flask, send_file, send_from_directory, request, jsonify
from flask_socketio import SocketIO, emit
import pyautogui
from email_service import send_email, build_url_email

EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')
STATIC_DIR = os.path.join(FRONTEND_DIR, 'static')

app = Flask(__name__, static_folder=None)
app.config['SECRET_KEY'] = os.urandom(24).hex()

def allowed_origin(origin):
    if not origin:
        return False
    allowed = {
        'http://localhost:5000',
        'http://127.0.0.1:5000',
        f'http://{get_local_ip()}:5000',
    }
    tunnel = get_tunnel_url()
    if tunnel:
        allowed.add(tunnel)
        allowed.add(tunnel.replace('https://', 'http://'))
    return origin in allowed

socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins=allowed_origin,
                    max_http_buffer_size=65536,
                    ping_interval=5, ping_timeout=3)

TUNNEL_URL_FILE = os.path.join(PROJECT_ROOT, '.tunnel_url')

cloudflared_proc = None
PAIRING_CODE = secrets.token_hex(3)
paired_sessions = {}
valid_tokens = set()
pair_failures = defaultdict(list)

# PII redaction filter
class PIIRedactFilter(logging.Filter):
    EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')
    URL_RE = re.compile(r'https?://[^\s]+')
    IP_RE = re.compile(r'\b(?!127\.)(?:\d{1,3}\.){3}\d{1,3}\b')

    def filter(self, record):
        msg = record.getMessage()
        msg = self.EMAIL_RE.sub('<email>', msg)
        msg = self.URL_RE.sub('<url>', msg)
        msg = self.IP_RE.sub('<ip>', msg)
        record.msg = msg
        record.args = ()
        return True

# Setup logging
LOG_DIR = os.path.join(PROJECT_ROOT, '.remote_mouse_logs')
os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'events.log')

logger = logging.getLogger('remote_mouse')
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.DEBUG)
file_handler.addFilter(PIIRedactFilter())
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S'))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(message)s', datefmt='%H:%M:%S'))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

def log_ok(msg):   logger.info(msg)
def log_info(msg): logger.debug(msg)
def log_warn(msg): logger.warning(msg)

# Action allowlist — only these socket events are permitted
ALLOWED_ACTIONS = {
    'mouse_move', 'mouse_abs', 'click', 'scroll', 'media',
    'mouse_down', 'mouse_up', 'request_tunnel_url', 'pair', 'disconnect'
}

# Blocked key combinations (OS-level dangerous combos)
BLOCKED_KEYS = {
    'ctrl+alt+del', 'ctrl+shift+esc', 'alt+f4', 'win+l',
    'win+r', 'win+x', 'win+d', 'alt+tab', 'ctrl+alt+tab',
}

class RateLimiter:
    def __init__(self, max_calls=30, window=1.0, action_limits=None):
        self.max_calls = max_calls
        self.window = window
        self.action_limits = action_limits or {}
        self._buckets = defaultdict(lambda: defaultdict(list))

    def check(self, sid, action):
        now = time.monotonic()
        limit = self.action_limits.get(action, self.max_calls)
        dq = self._buckets[sid][action]
        while dq and dq[0] < now - self.window:
            dq.pop(0)
        if len(dq) >= limit:
            return False
        dq.append(now)
        return True

    def cleanup(self, sid):
        self._buckets.pop(sid, None)

rate_limiter = RateLimiter(max_calls=30, window=1.0,
                           action_limits={'mouse_move': 120, 'mouse_abs': 120, 'scroll': 120})

# REST rate limits (keyed by remote IP)
rest_limiter = RateLimiter(max_calls=5, window=60)
setup_limiter = RateLimiter(max_calls=2, window=60)

def pairing_token_valid(token):
    return bool(token) and token in valid_tokens

def validate_action(action):
    if action not in ALLOWED_ACTIONS:
        log_warn(f"Blocked unknown action: {action}")
        return False
    return True

def get_local_ip():
    s = sock_lib.socket(sock_lib.AF_INET, sock_lib.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def cleanup():
    global cloudflared_proc
    if cloudflared_proc:
        log_info("Shutting down cloudflared...")
        cloudflared_proc.terminate()
        try:
            cloudflared_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cloudflared_proc.kill()
        cloudflared_proc = None

atexit.register(cleanup)

def get_tunnel_url():
    if os.path.exists(TUNNEL_URL_FILE):
        with open(TUNNEL_URL_FILE) as f:
            return f.read().strip()
    return None

setup_state = {
    'running': False,
    'done': False,
    'case': None,
    'email': None,
    'error': None,
    'logs': deque(maxlen=100),
}

def setup_log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    setup_state['logs'].append(line)
    print(line, flush=True)

def find_cloudflared():
    path = None
    # Use shutil.which for PATH resolution
    try:
        import shutil
        path = shutil.which('cloudflared') or shutil.which('cloudflared.exe')
    except Exception:
        pass
    if path:
        return path
    # Fallback: check common locations
    candidates = [
        os.path.expanduser('~/.cloudflared/cloudflared.exe'),
        r'C:\Program Files\cloudflared\cloudflared.exe',
        r'C:\tools\cloudflared\cloudflared.exe',
        '/usr/local/bin/cloudflared',
        '/usr/bin/cloudflared',
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def start_cloudflared():
    global cloudflared_proc
    if cloudflared_proc:
        setup_log("INFO Stopping existing cloudflared tunnel...")
        cloudflared_proc.terminate()
        try:
            cloudflared_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cloudflared_proc.kill()
        cloudflared_proc = None

    # Clear stale tunnel URL before starting fresh
    try: os.unlink(TUNNEL_URL_FILE)
    except FileNotFoundError: pass

    cf = find_cloudflared()
    if not cf:
        setup_log("ERROR cloudflared not found. Install from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
        setup_state['error'] = 'cloudflared not found'
        return None
    setup_log("INFO Starting cloudflared tunnel...")

    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.cloudflared', prefix='tunnel_', text=True)
    os.close(tmp_fd)  # close the fd immediately; we just need the path
    # Use direct file handle (not PIPE) to avoid eventlet GreenPipe deadlock on Windows
    out = open(tmp_path, 'w', encoding='utf-8')
    try:
        proc = subprocess.Popen(
            [cf, 'tunnel', '--url', 'http://localhost:5000'],
            stdout=out, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
    except:
        out.close()
        try: os.unlink(tmp_path)
        except: pass
        raise
    cloudflared_proc = proc

    url = None
    deadline = 45
    start = datetime.now()
    while (datetime.now() - start).total_seconds() < deadline:
        if proc.poll() is not None:
            # cloudflared exited — read whatever we got
            if os.path.exists(tmp_path):
                with open(tmp_path, encoding='utf-8', errors='replace') as f:
                    for line in f:
                        line = line.rstrip('\n\r')
                        if line:
                            setup_log(f"cloudflared {line[:120]}")
                        m = re.search(r'https?://[a-zA-Z0-9.-]+\.(trycloudflare\.com|cloudflare\.com|cf-test\.dev)', line)
                        if not m:
                            m = re.search(r'https?://[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]\.(cf|pages|dev)', line)
                        if m:
                            url = m.group(0)
                            setup_log(f"OK Tunnel URL: {url}")
                            break
            if not url:
                setup_log("ERROR cloudflared exited before providing a tunnel URL")
                setup_state['error'] = 'cloudflared exited'
            try: out.close()
            except: pass
            try: os.unlink(tmp_path)
            except: pass
            if url:
                with open(TUNNEL_URL_FILE, 'w') as f:
                    f.write(url + '\n')
            return url

        if os.path.exists(tmp_path):
            try:
                with open(tmp_path, encoding='utf-8', errors='replace') as f:
                    for line in f:
                        line = line.rstrip('\n\r')
                        if line:
                            setup_log(f"cloudflared {line[:120]}")
                        m = re.search(r'https?://[a-zA-Z0-9.-]+\.(trycloudflare\.com|cloudflare\.com|cf-test\.dev)', line)
                        if not m:
                            m = re.search(r'https?://[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]\.(cf|pages|dev)', line)
                        if m:
                            url = m.group(0)
                            setup_log(f"OK Tunnel URL: {url}")
                            break
                if url:
                    break
            except (IOError, OSError):
                pass

        time.sleep(0.5)

    try: out.close()
    except: pass
    try: os.unlink(tmp_path)
    except: pass

    if not url:
        setup_log("ERROR cloudflared timed out (45s) — no tunnel URL received")
        setup_state['error'] = 'cloudflared timed out'
        return None

    with open(TUNNEL_URL_FILE, 'w') as f:
        f.write(url + '\n')
    return url

@app.after_request
def add_security_headers(resp):
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-XSS-Protection'] = '0'
    resp.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; connect-src 'self' ws://* wss://*; img-src 'self' data:; frame-ancestors 'none'"
    resp.headers['Referrer-Policy'] = 'no-referrer'
    resp.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return resp

@app.route('/')
def index():
    resp = send_file(os.path.join(FRONTEND_DIR, 'index.html'))
    resp.headers['Cache-Control'] = 'no-cache, must-revalidate'
    return resp

@app.route('/favicon.ico')
def favicon():
    return '', 204

ALLOWED_STATIC_EXTS = ('.js', '.css', '.png', '.ico', '.svg', '.json', '.map')
@app.route('/static/<path:filename>')
def static_files(filename):
    if not filename.lower().endswith(ALLOWED_STATIC_EXTS):
        log_warn(f"Blocked static file access: {filename}")
        return '', 404
    resp = send_from_directory(STATIC_DIR, filename)
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp

@app.route('/api/tunnel-url')
def api_tunnel_url():
    token = request.args.get('token') or request.headers.get('X-Pairing-Token', '')
    if not pairing_token_valid(token):
        return jsonify({'error': 'Not paired'}), 403
    return jsonify({
        'url': get_tunnel_url() or '',
        'local_ip': get_local_ip()
    })

@app.route('/setup')
def setup_page():
    resp = send_file(os.path.join(FRONTEND_DIR, 'setup.html'))
    resp.headers['Cache-Control'] = 'no-cache, must-revalidate'
    return resp

@app.route('/api/setup-start', methods=['POST'])
def api_setup_start():
    if not setup_limiter.check(request.remote_addr, 'setup-start'):
        return jsonify({'error': 'Too many requests. Wait a minute.'}), 429
    data = request.get_json() or {}
    case = data.get('case')
    email = (data.get('email') or '').strip()

    if case not in ('same-wifi', 'remote', 'localhost'):
        return jsonify({'error': 'Invalid case. Choose same-wifi, remote, or localhost'}), 400
    if case == 'remote' and (not email or not EMAIL_RE.match(email)):
        return jsonify({'error': 'Email required for remote access'}), 400

    setup_state['logs'].clear()
    setup_state['running'] = True
    setup_state['done'] = False
    setup_state['case'] = case
    setup_state['email'] = email
    setup_state['error'] = None

    def run():
        try:
            if case == 'localhost':
                setup_log("OK Case: Localhost (same machine)")
                setup_log(f"INFO Open http://127.0.0.1:5000 in your browser")
            elif case == 'same-wifi':
                ip = get_local_ip()
                setup_log("OK Case: Same WiFi")
                setup_log(f"INFO Open http://{ip}:5000 on your phone")
            elif case == 'remote':
                setup_log("OK Case: Remote (different networks)")
                url = start_cloudflared()
                if url:
                    ip = get_local_ip()
                    setup_log(f"OK Local: http://{ip}:5000")
                    setup_log(f"OK Tunnel: {url}")
                    if email:
                        try:
                            html = build_url_email(url)
                            send_email(email, 'Remote Mouse - Tunnel URL', html)
                            setup_log(f"OK Email sent to {email}")
                        except Exception as e:
                            setup_log(f"ERROR Failed to send email: {e}")
                else:
                    setup_log("ERROR Cloudflared failed to start")
        except Exception as e:
            setup_log(f"ERROR {e}")
            setup_state['error'] = str(e)
        finally:
            setup_state['running'] = False
            setup_state['done'] = True

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'success': True})

@app.route('/api/setup-status')
def api_setup_status():
    return jsonify({
        'running': setup_state['running'],
        'done': setup_state['done'],
        'case': setup_state['case'],
        'email': bool(setup_state['email']),
        'error': setup_state['error'],
        'tunnel_url': get_tunnel_url() or '',
        'local_ip': get_local_ip(),
        'logs': list(setup_state['logs']),
    })

@app.route('/api/send-url', methods=['POST'])
def api_send_url():
    if not rest_limiter.check(request.remote_addr, 'send-url'):
        return jsonify({'error': 'Too many requests. Wait a minute.'}), 429
    data = request.get_json() or {}
    token = data.get('token') or request.headers.get('X-Pairing-Token', '')
    if not pairing_token_valid(token):
        return jsonify({'error': 'Not paired. Re-open index.html on your phone.'}), 403
    email = (data.get('email') or '').strip()
    if not email or not EMAIL_RE.match(email):
        return jsonify({'error': 'Invalid email address'}), 400
    url = get_tunnel_url()
    if not url:
        return jsonify({'error': 'No tunnel URL available'}), 400
    try:
        html = build_url_email(url)
        send_email(email, 'Remote Mouse - Tunnel URL', html)
        log_ok(f"Email sent to {email}")
        return jsonify({'success': True, 'message': f'Tunnel URL sent to {email}'})
    except Exception as e:
        return jsonify({'error': f'Failed to send email: {str(e)}'}), 500

def with_ratelimit(action):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if not validate_action(action):
                return
            if not rate_limiter.check(request.sid, action):
                log_warn(f"Rate limit exceeded: {action}")
                return
            return f(*args, **kwargs)
        return wrapper
    return decorator

def require_auth():
    sid = request.sid
    if sid not in paired_sessions:
        return False
    return bool(paired_sessions[sid].get('token'))

@socketio.on('connect')
def handle_connect(auth):
    rate_limiter.cleanup(request.sid)
    token = (auth or {}).get('token', '')
    is_paired = bool(token) and token in valid_tokens
    if token and not is_paired:
        log_warn("Rejected connection with invalid token")
        raise ConnectionRefusedError('unauthorized')

    paired_sessions[request.sid] = paired_sessions.get(request.sid, {})
    paired_sessions[request.sid]['connected'] = True
    if is_paired:
        paired_sessions[request.sid]['token'] = token
        log_ok("Client connected (authenticated)")
        w, h = pyautogui.size()
        emit('screen_info', {
            'width': w, 'height': h,
            'ip': get_local_ip(),
            'tunnel_url': get_tunnel_url() or ''
        })
    else:
        log_info("Client connected (unauthenticated)")

@socketio.on('pair')
@with_ratelimit('pair')
def handle_pair(data):
    sid = request.sid
    now = time.time()
    pair_failures[sid] = [t for t in pair_failures[sid] if now - t < 60]
    if len(pair_failures[sid]) >= 5:
        log_warn("Pairing lockout: too many failures")
        emit('pair_error', {'message': 'Too many attempts. Wait 60 seconds.'})
        return
    code = (data or {}).get('code', '').strip().lower()
    if code == PAIRING_CODE:
        token = secrets.token_urlsafe(32)
        valid_tokens.add(token)
        paired_sessions[sid] = {'token': token, 'paired_at': now, 'connected': True}
        pair_failures.pop(sid, None)
        emit('paired', {'token': token})
        log_ok("Client paired successfully")
    else:
        pair_failures[sid].append(now)
        emit('pair_error', {'message': 'Invalid pairing code'})
        log_warn("Failed pairing attempt")

@socketio.on('disconnect')
def handle_disconnect():
    rate_limiter.cleanup(request.sid)
    pair_failures.pop(request.sid, None)
    paired_sessions.pop(request.sid, None)
    log_info("Client disconnected")

@socketio.on('request_tunnel_url')
@with_ratelimit('request_tunnel_url')
def handle_request_tunnel_url():
    if not require_auth(): return
    url = get_tunnel_url()
    if url:
        emit('tunnel_url', {'url': url})

@socketio.on('mouse_move')
@with_ratelimit('mouse_move')
def handle_move(data):
    if not require_auth(): return
    dx = data.get('dx', 0)
    dy = data.get('dy', 0)
    if dx != 0 or dy != 0:
        pyautogui.moveRel(int(dx), int(dy), _pause=False)
        log_info(f"move ({dx:+04}, {dy:+04})")

@socketio.on('mouse_abs')
@with_ratelimit('mouse_abs')
def handle_mouse_abs(data):
    if not require_auth(): return
    w, h = pyautogui.size()
    x = max(0, min(w, int(data.get('x', 0))))
    y = max(0, min(h, int(data.get('y', 0))))
    pyautogui.moveTo(x, y, _pause=False)
    log_info(f"abs  ({x:04}, {y:04})")

@socketio.on('click')
@with_ratelimit('click')
def handle_click(data):
    if not require_auth(): return
    button = data.get('button', 'left')
    if button in ('back', 'forward'):
        _browser_navigate(button)
    else:
        pyautogui.click(button=button, _pause=False)
    log_info(f"click {button}")


def _browser_navigate(direction):
    combo = f"alt+{'left' if direction == 'back' else 'right'}"
    if combo in BLOCKED_KEYS:
        log_warn(f"Blocked dangerous key combo: {combo}")
        return
    if platform.system() == 'Windows':
        key = 'browserback' if direction == 'back' else 'browserforward'
        pyautogui.press(key, _pause=False)
    elif platform.system() == 'Darwin':
        pyautogui.hotkey('command', 'left' if direction == 'back' else 'right', _pause=False)
    else:
        pyautogui.hotkey('alt', 'left' if direction == 'back' else 'right', _pause=False)

@socketio.on('mouse_down')
@with_ratelimit('mouse_down')
def handle_mouse_down(data=None):
    if not require_auth(): return
    try:
        pyautogui.mouseDown(button='left', _pause=False)
        log_info("mouse_down")
    except Exception as e:
        log_warn(f"mouse_down failed: {e}")

@socketio.on('mouse_up')
@with_ratelimit('mouse_up')
def handle_mouse_up(data=None):
    if not require_auth(): return
    try:
        pyautogui.mouseUp(button='left', _pause=False)
        log_info("mouse_up")
    except Exception as e:
        log_warn(f"mouse_up failed: {e}")

@socketio.on('scroll')
@with_ratelimit('scroll')
def handle_scroll(data):
    if not require_auth(): return
    dx = data.get('dx', 0)
    dy = data.get('dy', 0)
    if dy != 0:
        clicks = max(1, abs(int(dy / 20)))
        pyautogui.scroll(-clicks if dy > 0 else clicks, _pause=False)
        log_info(f"scroll v({dy:+05})")
    if dx != 0:
        clicks = max(1, abs(int(dx / 20)))
        pyautogui.hscroll(clicks if dx > 0 else -clicks, _pause=False)
        log_info(f"scroll h({dx:+05})")

@socketio.on('media')
@with_ratelimit('media')
def handle_media(data):
    if not require_auth(): return
    action = data.get('action', '')
    key_map = {
        'play_pause': 'playpause',
        'next': 'nexttrack',
        'prev': 'prevtrack',
        'vol_up': 'volumeup',
        'vol_down': 'volumedown',
        'mute': 'volumemute',
    }
    key = key_map.get(action)
    if key:
        pyautogui.press(key, _pause=False)
        log_info(f"media {action}")

def run_server():
    # Clear stale tunnel URL from previous session
    try: os.unlink(TUNNEL_URL_FILE)
    except FileNotFoundError: pass

    ip = get_local_ip()
    tunnel = get_tunnel_url()
    log_ok("Remote Mouse v1.1.1 starting on port 5000...")
    log_info(f"Local: http://{ip}:5000")
    if tunnel:
        log_info(f"Tunnel: {tunnel}")
    log_ok(f"Pairing code: {PAIRING_CODE}")
    log_ok("WebSocket ready")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    run_server()
