import eventlet
eventlet.monkey_patch()

import os
import re
import subprocess
import socket as sock_lib
import threading
import time
import atexit
from datetime import datetime
from collections import deque
from flask import Flask, send_file, send_from_directory, request, jsonify
from flask_socketio import SocketIO, emit
import pyautogui
from email_service import send_email, build_url_email

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')
STATIC_DIR = os.path.join(FRONTEND_DIR, 'static')

app = Flask(__name__, static_folder=None)
app.config['SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*", ping_interval=5, ping_timeout=3)

TUNNEL_URL_FILE = os.path.join(PROJECT_ROOT, '.tunnel_url')
EVENT_LOG_FILE = os.path.join(PROJECT_ROOT, 'events.log')
cloudflared_proc = None

def _log(level, msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f"[{ts}] {level} {msg}"
    print(line, flush=True)
    try:
        with open(EVENT_LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception as e:
        fallback = f"[{ts}] ERROR Failed to write to {EVENT_LOG_FILE}: {e}"
        print(fallback, flush=True)

def log_ok(msg):   _log('OK', msg)
def log_info(msg): _log('INFO', msg)
def log_warn(msg): _log('WARN', msg)

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
    candidates = ['cloudflared', 'cloudflared.exe']
    for c in candidates:
        try:
            r = subprocess.run([c, '--version'], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return c
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    extra = [
        os.path.expanduser('~/.cloudflared/cloudflared.exe'),
        r'C:\Program Files\cloudflared\cloudflared.exe',
        r'C:\tools\cloudflared\cloudflared.exe',
        '/usr/local/bin/cloudflared',
        '/usr/bin/cloudflared',
    ]
    for p in extra:
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

    tmp_path = os.path.join(PROJECT_ROOT, '.cloudflared_output')
    # Use direct file handle (not PIPE) to avoid eventlet GreenPipe deadlock on Windows
    with open(tmp_path, 'w', encoding='utf-8') as out:
        proc = subprocess.Popen(
            [cf, 'tunnel', '--url', 'http://localhost:5000'],
            stdout=out, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
    cloudflared_proc = proc

    url = None
    deadline = 30
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
                        m = re.search(r'https?://[a-zA-Z0-9.-]+\.trycloudflare\.com', line)
                        if m:
                            url = m.group(0)
                            setup_log(f"OK Tunnel URL: {url}")
                            break
            if not url:
                setup_log("ERROR cloudflared exited before providing a tunnel URL")
                setup_state['error'] = 'cloudflared exited'
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
                        m = re.search(r'https?://[a-zA-Z0-9.-]+\.trycloudflare\.com', line)
                        if m:
                            url = m.group(0)
                            setup_log(f"OK Tunnel URL: {url}")
                            break
                if url:
                    break
            except (IOError, OSError):
                pass

        time.sleep(0.5)

    try: os.unlink(tmp_path)
    except: pass

    if not url:
        setup_log("ERROR cloudflared timed out (30s) — no tunnel URL received")
        setup_state['error'] = 'cloudflared timed out'
        return None

    with open(TUNNEL_URL_FILE, 'w') as f:
        f.write(url + '\n')
    return url

@app.route('/')
def index():
    resp = send_file(os.path.join(FRONTEND_DIR, 'index.html'))
    resp.headers['Cache-Control'] = 'no-cache, must-revalidate'
    return resp

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/static/<path:filename>')
def static_files(filename):
    resp = send_from_directory(STATIC_DIR, filename)
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp

@app.route('/api/tunnel-url')
def api_tunnel_url():
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
    data = request.get_json() or {}
    case = data.get('case')
    email = (data.get('email') or '').strip()

    if case not in ('same-wifi', 'remote', 'localhost'):
        return jsonify({'error': 'Invalid case. Choose same-wifi, remote, or localhost'}), 400
    if case == 'remote' and (not email or '@' not in email):
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
    data = request.get_json()
    email = (data.get('email') or '').strip()
    if not email or '@' not in email or '.' not in email:
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

@socketio.on('connect')
def handle_connect():
    w, h = pyautogui.size()
    log_ok("Client connected")
    emit('screen_info', {
        'width': w, 'height': h,
        'ip': get_local_ip(),
        'tunnel_url': get_tunnel_url() or ''
    })

@socketio.on('disconnect')
def handle_disconnect():
    log_info("Client disconnected")

@socketio.on('request_tunnel_url')
def handle_request_tunnel_url():
    url = get_tunnel_url()
    if url:
        emit('tunnel_url', {'url': url})

@socketio.on('mouse_move')
def handle_move(data):
    dx = data.get('dx', 0)
    dy = data.get('dy', 0)
    if dx != 0 or dy != 0:
        pyautogui.moveRel(int(dx), int(dy), _pause=False)
        log_info(f"move ({dx:+04}, {dy:+04})")

@socketio.on('mouse_abs')
def handle_mouse_abs(data):
    w, h = pyautogui.size()
    x = max(0, min(w, int(data.get('x', 0))))
    y = max(0, min(h, int(data.get('y', 0))))
    pyautogui.moveTo(x, y, _pause=False)
    log_info(f"abs  ({x:04}, {y:04})")

@socketio.on('click')
def handle_click(data):
    button = data.get('button', 'left')
    pyautogui.click(button=button, _pause=False)
    log_info(f"click {button}")

@socketio.on('scroll')
def handle_scroll(data):
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
def handle_media(data):
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
    log_ok("Remote Mouse v1.0.0 starting on port 5000...")
    log_info(f"Local: http://{ip}:5000")
    if tunnel:
        log_info(f"Tunnel: {tunnel}")
    log_ok("WebSocket ready")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    run_server()
