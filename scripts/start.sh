#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo "=== Remote Mouse Launcher ==="

# 1. Check Python
if ! command -v python3 &>/dev/null; then
  echo "[FAIL] Python3 not found. Install Python 3.10+"
  exit 1
fi
echo "[OK] $(python3 --version)"

# 2. Install deps
echo "[...] Installing dependencies..."
python3 -m pip install -r requirements.txt --quiet 2>/dev/null

# 3. Check cloudflared
HAS_CLOUDFLARED=false
if command -v cloudflared &>/dev/null; then
  echo "[OK] $(cloudflared version)"
  HAS_CLOUDFLARED=true
else
  echo "[WARN] cloudflared not found. Install from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
  echo "[WARN] Falling back to local network only."
fi

# 4. Start Python server
echo "[...] Starting server..."
python3 src/server.py &
SERVER_PID=$!
sleep 2

if ! kill -0 $SERVER_PID 2>/dev/null; then
  echo "[FAIL] Server failed to start."
  exit 1
fi
echo "[OK] Server running on port 5000"

# 5. Start tunnel
TUNNEL_URL=""
if $HAS_CLOUDFLARED; then
  echo "[...] Starting Cloudflare tunnel..."
  TUNNEL_LOG="$PROJECT_ROOT/tunnel.log"
  cloudflared tunnel --url http://localhost:5000 --logfile "$TUNNEL_LOG" &
  TUNNEL_PID=$!

  echo "[...] Waiting for tunnel URL..."
  for i in $(seq 1 30); do
    sleep 1
    if [ -f "$TUNNEL_LOG" ]; then
      TUNNEL_URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" | head -1)
      if [ -n "$TUNNEL_URL" ]; then
        break
      fi
    fi
  done

  if [ -n "$TUNNEL_URL" ]; then
    echo "[OK] Tunnel URL: $TUNNEL_URL"
    echo "$TUNNEL_URL" > "$PROJECT_ROOT/.tunnel_url"
  else
    echo "[WARN] Could not extract tunnel URL from logs."
  fi
fi

# 6. Print access info
echo ""
echo "======================================"
echo "  Remote Mouse is running!"
echo "======================================"
echo ""

if [ -n "$TUNNEL_URL" ]; then
  echo "  Internet:    $TUNNEL_URL"
fi

LOCAL_IP=$(ip route get 1 2>/dev/null | awk '{print $NF;exit}' || ifconfig 2>/dev/null | grep 'inet ' | awk 'NR==1{print $2}')
if [ -n "$LOCAL_IP" ]; then
  echo "  Local:       http://${LOCAL_IP}:5000"
fi
echo "  Local:       http://127.0.0.1:5000"
echo ""
echo "Open the URL on your phone to start controlling."
echo ""
echo "Press Ctrl+C to stop."
echo ""

cleanup() {
  kill "$SERVER_PID" 2>/dev/null
  [ -n "${TUNNEL_PID:-}" ] && kill "$TUNNEL_PID" 2>/dev/null
  rm -f "$PROJECT_ROOT/.tunnel_url"
  exit
}
trap cleanup INT TERM
wait
