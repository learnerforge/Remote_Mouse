import smtplib
import logging
import sys
import time
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("touchmorph.email")

SMTP_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_DELAY = 2


class EmailService:
    def __init__(self, config):
        self.config = config

    def _get_cfg(self):
        return self.config.smtp_host, self.config.smtp_port, self.config.smtp_user, \
            self.config.smtp_pass, self.config.email_from, self.config.email_to

    def _build_message(self, tunnel_url: str) -> MIMEMultipart:
        _, _, _, _, email_from, email_to = self._get_cfg()
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
        msg["From"] = email_from
        msg["To"] = email_to
        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))
        return msg

    def _build_generic_message(self, subject: str, body: str) -> MIMEText:
        _, _, _, _, email_from, email_to = self._get_cfg()
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = email_from
        msg["To"] = email_to
        return msg

    def send_tunnel_url(self, tunnel_url: str) -> bool:
        host, port, user, password, _, _ = self._get_cfg()
        if not all([host, user, password]):
            logger.warning("SMTP not configured — printing URL to console")
            print(f"\n[TouchMorph] TUNNEL URL: {tunnel_url}\n")
            return False
        msg = self._build_message(tunnel_url)
        return self._send(host, port, user, password, msg)

    def send_email(self, subject: str, body: str) -> bool:
        host, port, user, password, _, _ = self._get_cfg()
        if not all([host, user, password]):
            logger.warning("SMTP not configured")
            return False
        msg = self._build_generic_message(subject, body)
        return self._send(host, port, user, password, msg)

    def _send(self, host, port, user, password, msg) -> bool:
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if port == 465:
                    with smtplib.SMTP_SSL(host, port, timeout=SMTP_TIMEOUT) as server:
                        server.login(user, password)
                        server.send_message(msg)
                else:
                    with smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT) as server:
                        if port == 587:
                            server.starttls()
                        if user:
                            server.login(user, password)
                        server.send_message(msg)
                logger.info(f"Email sent successfully (attempt {attempt})")
                return True
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt}/{MAX_RETRIES} failed: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
        logger.error(f"All {MAX_RETRIES} attempts failed: {last_error}")
        return False

    def test_config(self) -> bool:
        host, port, user, password, email_from, email_to = self._get_cfg()
        if not all([host, user, password, email_from, email_to]):
            print("SMTP config incomplete. Check .env or /api/setup/email")
            return False
        print(f"Testing SMTP: {user} @ {host}:{port} -> {email_to}")
        msg = self._build_generic_message(
            "TouchMorph SMTP Test",
            "TouchMorph SMTP test \u2014 successful!",
        )
        return self._send(host, port, user, password, msg)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from config import Config
    cfg = Config()
    svc = EmailService(cfg)
    if len(sys.argv) == 3 and sys.argv[1] == "--send":
        svc.send_tunnel_url(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == "--test":
        sys.exit(0 if svc.test_config() else 1)
    else:
        print("Usage:")
        print("  python email_service.py --send <tunnel_url>")
        print("  python email_service.py --test")
