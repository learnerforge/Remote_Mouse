import os
import hashlib
import hmac
import time
from dotenv import load_dotenv
from pathlib import Path

dotenv_path = Path(__file__).resolve().parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)


class Config:
    VERSION = "1.0.0"

    def __init__(self):
        self.host = os.getenv("TOUCHMORPH_HOST", "0.0.0.0")
        self.port = int(os.getenv("TOUCHMORPH_PORT", "3000"))
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self.email_from = os.getenv("EMAIL_FROM", "")
        self.email_to = os.getenv("EMAIL_TO", "")
        self.admin_password = os.getenv("ADMIN_PASSWORD", "")
        self.admin_secret = os.getenv("ADMIN_SECRET", "touchmorph-dev-secret-change-me")

    def get_client_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / "client" / "dist"

    def get_admin_token(self) -> str:
        if not self.admin_password:
            return ""
        random_hex = os.urandom(16).hex()
        timestamp = str(int(time.time()))
        raw = f"{random_hex}:{timestamp}"
        sig = hmac.new(self.admin_secret.encode(), raw.encode(), hashlib.sha256).hexdigest()[:16]
        return f"{raw}:{sig}"

    def set_email_config(self, host, port, user, password, from_email, to_email):
        self.smtp_host = host
        self.smtp_port = port
        self.smtp_user = user
        self.smtp_pass = password
        self.email_from = from_email
        self.email_to = to_email
        import logging
        logging.getLogger("touchmorph").warning(
            "Email config stored in memory only — will be lost on restart. "
            "To persist, add SMTP_* variables to your .env file."
        )
