import smtplib
import logging
import sys
import time
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

_parent = Path(__file__).resolve().parent
sys.path.insert(0, str(_parent))

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_FROM, EMAIL_TO

logger = logging.getLogger("touchmorph.email")

SMTP_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_DELAY = 2


def _build_message(tunnel_url: str) -> MIMEMultipart:
    subject = "Your TouchMorph Tunnel is Ready"

    text = f"""Your TouchMorph secure tunnel is active.

URL: {tunnel_url}

Open this URL in your phone browser to control your PC.
This link is secure and encrypted via Cloudflare.

The link will expire when the tunnel stops.
"""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:system-ui,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td style="padding:40px 16px">
<table width="480" cellpadding="0" cellspacing="0" style="margin:0 auto;background:#1e293b;border-radius:16px">
<tr><td style="padding:32px">
<h1 style="color:#818cf8;font-size:24px;margin:0 0 8px">TouchMorph</h1>
<p style="color:#94a3b8;font-size:14px;margin:0 0 24px">Your secure tunnel is active</p>
<div style="background:#0f172a;border-radius:12px;padding:16px;text-align:center;margin-bottom:24px">
<a href="{tunnel_url}" style="color:#a5b4fc;font-size:18px;text-decoration:none;word-break:break-all">{tunnel_url}</a>
</div>
<p style="color:#64748b;font-size:13px;margin:0 0 8px">Open this link in your phone browser to control your PC.</p>
<p style="color:#64748b;font-size:13px;margin:0">Encrypted via Cloudflare &middot; Expires when tunnel stops</p>
</td></tr></table>
</td></tr></table>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))
    return msg


def send_tunnel_url(tunnel_url: str) -> bool:
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS, EMAIL_FROM, EMAIL_TO]):
        logger.warning("SMTP not configured — printing URL to console")
        print(f"\n[TouchMorph] TUNNEL URL: {tunnel_url}\n")
        return False

    msg = _build_message(tunnel_url)

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if SMTP_PORT == 465:
                with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
                    server.login(SMTP_USER, SMTP_PASS)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
                    if SMTP_PORT == 587:
                        server.starttls()
                    if SMTP_USER:
                        server.login(SMTP_USER, SMTP_PASS)
                    server.send_message(msg)
            logger.info(f"Tunnel URL sent to {EMAIL_TO} (attempt {attempt})")
            return True
        except Exception as e:
            last_error = e
            logger.warning(f"Attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    logger.error(f"All {MAX_RETRIES} attempts failed: {last_error}")
    print(f"\n[TouchMorph] TUNNEL URL (email failed): {tunnel_url}\n")
    return False


def test_config() -> bool:
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS, EMAIL_FROM, EMAIL_TO]):
        print("SMTP config incomplete. Check SMTP_HOST, SMTP_USER, SMTP_PASS, EMAIL_FROM, EMAIL_TO in .env")
        return False

    print(f"Testing SMTP: {SMTP_USER} @ {SMTP_HOST}:{SMTP_PORT} -> {EMAIL_TO}")
    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
                server.login(SMTP_USER, SMTP_PASS)
                msg = MIMEText("TouchMorph SMTP test — successful!")
                msg["Subject"] = "TouchMorph SMTP Test"
                msg["From"] = EMAIL_FROM
                msg["To"] = EMAIL_TO
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
                if SMTP_PORT == 587:
                    server.starttls()
                if SMTP_USER:
                    server.login(SMTP_USER, SMTP_PASS)
                msg = MIMEText("TouchMorph SMTP test — successful!")
                msg["Subject"] = "TouchMorph SMTP Test"
                msg["From"] = EMAIL_FROM
                msg["To"] = EMAIL_TO
                server.send_message(msg)
        print("OK — test email sent successfully.")
        return True
    except Exception as e:
        print(f"FAILED — {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) == 3 and sys.argv[1] == "--send":
        send_tunnel_url(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == "--test":
        sys.exit(0 if test_config() else 1)
    else:
        print("Usage:")
        print("  python email_service.py --send <tunnel_url>")
        print("  python email_service.py --test")
