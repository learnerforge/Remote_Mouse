#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-3000}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "TouchMorph - Cloudflare Tunnel"
echo ""

if ! command -v cloudflared &>/dev/null; then
  echo "cloudflared not found. Install from: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
  exit 1
fi

echo "Starting tunnel to localhost:$PORT ..."

TUNNEL_URL=$(cloudflared tunnel --url "http://localhost:$PORT" 2>&1 | grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' | head -1)

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║  SECURE HTTPS TUNNEL ACTIVE                   ║"
echo "║                                               ║"
echo "║  $TUNNEL_URL"
echo "║                                               ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

if [ -f "$PROJECT_DIR/server/email_service.py" ]; then
  python3 "$PROJECT_DIR/server/email_service.py" --send "$TUNNEL_URL" 2>/dev/null || true
fi

echo "Press Ctrl+C to stop."
wait
