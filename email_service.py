import os
import smtplib
import ssl
import time
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

DEFAULT_SMTP_PORT = 587

def load_env():
    env = {}
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    env[k.strip()] = v.strip()
    return env

def send_email(recipient, subject, body_html):
    config = load_env()

    smtp_host = config.get('SMTP_HOST') or os.environ.get('SMTP_HOST')
    smtp_port = int(config.get('SMTP_PORT') or os.environ.get('SMTP_PORT', str(DEFAULT_SMTP_PORT)))
    smtp_user = config.get('SMTP_USERNAME') or os.environ.get('SMTP_USERNAME')
    smtp_pass = config.get('SMTP_PASSWORD') or os.environ.get('SMTP_PASSWORD')
    from_addr = config.get('SMTP_FROM_EMAIL') or os.environ.get('SMTP_FROM_EMAIL') or smtp_user
    to_addr = recipient or config.get('SMTP_TO_EMAIL') or os.environ.get('SMTP_TO_EMAIL')

    if not all([smtp_host, smtp_user, smtp_pass, to_addr]):
        raise ValueError('Missing SMTP configuration. Check .env file or environment variables.')

    msg = MIMEMultipart('alternative')
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg.attach(MIMEText(body_html, 'html'))

    context = ssl.create_default_context()

    for attempt in range(3):
        try:
            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=15) as server:
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(from_addr, to_addr, msg.as_string())
            else:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                    server.starttls(context=context)
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(from_addr, to_addr, msg.as_string())
            print(f'Email sent to {to_addr}')
            return True
        except Exception as e:
            print(f'Attempt {attempt + 1} failed: {e}')
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise

def build_url_email(tunnel_url):
    return f'''<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; padding: 24px; background: #f5f5f5;">
<div style="max-width: 480px; margin: 0 auto; background: white; border-radius: 12px; padding: 32px; box-shadow: 0 2px 12px rgba(0,0,0,0.1);">
  <h2 style="margin-top: 0; color: #333;">Remote Mouse Ready</h2>
  <p style="color: #666; font-size: 14px;">Tap the link below to control your laptop from your phone:</p>
  <a href="{tunnel_url}" style="display: block; padding: 16px; background: #4ade80; color: #000; text-decoration: none; border-radius: 8px; font-size: 14px; font-weight: 600; text-align: center; word-break: break-all; margin: 20px 0;">
    {tunnel_url}
  </a>
  <p style="color: #999; font-size: 12px;">This link is temporary and will expire when the tunnel stops.</p>
</div>
</body>
</html>'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Send tunnel URL via email')
    parser.add_argument('--send', help='Tunnel URL to send')
    parser.add_argument('--test', action='store_true', help='Send a test email')
    args = parser.parse_args()

    if args.send:
        html = build_url_email(args.send)
        send_email(None, 'Remote Mouse - Tunnel URL', html)
        print('Tunnel URL sent via email.')
    elif args.test:
        html = '<h2>Test Email</h2><p>If you receive this, SMTP is configured correctly.</p>'
        send_email(None, 'Remote Mouse - Test Email', html)
        print('Test email sent.')
    else:
        parser.print_help()
