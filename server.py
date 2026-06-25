import eventlet
eventlet.monkey_patch()

import os
import socket as sock_lib
from datetime import datetime
from collections import deque
from flask import Flask, send_file, send_from_directory, request, jsonify
from flask_socketio import SocketIO, emit
import pyautogui
from email_service import send_email, build_url_email

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*", ping_interval=5, ping_timeout=3)

TUNNEL_URL_FILE = '.tunnel_url'
EVENT_LOG_FILE = 'events.log'

log_history = deque(maxlen=200)

def log_msg(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    log_history.append(line)
    print(line, flush=True)
    try:
        with open(EVENT_LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except:
        pass

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

def get_tunnel_url():
    if os.path.exists(TUNNEL_URL_FILE):
        with open(TUNNEL_URL_FILE) as f:
            return f.read().strip()
    return None

@app.route('/')
def index():
    resp = send_file('index.html')
    resp.headers['Cache-Control'] = 'no-cache, must-revalidate'
    return resp

@app.route('/static/<path:filename>')
def static_files(filename):
    resp = send_from_directory('static', filename)
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp

@app.route('/api/tunnel-url')
def api_tunnel_url():
    return jsonify({
        'url': get_tunnel_url() or '',
        'local_ip': get_local_ip()
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
        log_msg(f"* Email sent to {email}")
        return jsonify({'success': True, 'message': f'Tunnel URL sent to {email}'})
    except Exception as e:
        return jsonify({'error': f'Failed to send email: {str(e)}'}), 500

@socketio.on('connect')
def handle_connect():
    w, h = pyautogui.size()
    log_msg("* Client connected")
    emit('screen_info', {
        'width': w, 'height': h,
        'ip': get_local_ip(),
        'tunnel_url': get_tunnel_url() or ''
    })

@socketio.on('disconnect')
def handle_disconnect():
    log_msg("* Client disconnected")

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
        log_msg(f"> move   ({dx:+04}, {dy:+04})")

@socketio.on('mouse_down')
def handle_down(data):
    pyautogui.mouseDown(button=data.get('button', 'left'), _pause=False)
    log_msg(f"> down   {data.get('button', 'left')}")

@socketio.on('mouse_up')
def handle_up(data):
    pyautogui.mouseUp(button=data.get('button', 'left'), _pause=False)
    log_msg(f"> up     {data.get('button', 'left')}")

@socketio.on('click')
def handle_click(data):
    button = data.get('button', 'left')
    pyautogui.click(button=button, _pause=False)
    log_msg(f"> click  {button}")

@socketio.on('double_click')
def handle_double_click():
    pyautogui.doubleClick(_pause=False)
    log_msg(f"> dblclick")

@socketio.on('scroll')
def handle_scroll(data):
    dy = data.get('dy', 0)
    if dy != 0:
        clicks = max(1, abs(int(dy / 20)))
        pyautogui.scroll(-clicks if dy > 0 else clicks, _pause=False)
        log_msg(f"> scroll ({dy:+05})")

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
        log_msg(f"> media  {action}")

@socketio.on('key')
def handle_key(data):
    action = data.get('action', '')
    key_map = {
        'alt_tab': ('alt', 'tab'),
        'win_d': ('win', 'd'),
        'win_tab': ('win', 'tab'),
        'win_l': ('win', 'l'),
        'esc': ('esc',),
        'enter': ('enter',),
        'space': ('space',),
    }
    keys = key_map.get(action)
    if keys:
        if len(keys) == 1:
            pyautogui.press(keys[0], _pause=False)
        else:
            pyautogui.hotkey(*keys, _pause=False)
        log_msg(f"> key    {action}")

def run_server():
    ip = get_local_ip()
    tunnel = get_tunnel_url()
    log_msg(f"* Server starting on port 5000...")
    log_msg(f"* Local:  http://{ip}:5000")
    if tunnel:
        log_msg(f"* Tunnel: {tunnel}")
    log_msg(f"* WebSocket ready")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    run_server()
