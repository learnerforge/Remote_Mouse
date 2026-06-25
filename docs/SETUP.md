# Setup Guide

This guide walks you through setting up Remote Mouse from scratch — from installing Python to connecting your phone for the first time.

## Prerequisites

### Required

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.10+ | Runs the server and CLI |
| pip | (included with Python) | Installs Python packages |

### Optional

| Software | Purpose |
|----------|---------|
| cloudflared | Creates a secure HTTPS tunnel for remote access over the internet |
| SMTP account | Sends the tunnel URL to your phone via email |
| Git | Cloning the repository (or download the ZIP) |

## Step 1: Get the Code

### Option A: Clone with Git

```bash
git clone <repository-url> remote-mouse
cd remote-mouse
```

### Option B: Download ZIP

Download the ZIP archive from the repository and extract it to a folder called `remote-mouse`.

## Step 2: Install Python Dependencies

Open a terminal (Command Prompt, Powershell, or Bash) in the project directory:

```bash
pip install -r requirements.txt
```

This installs:

| Package | Purpose |
|---------|---------|
| `flask` | HTTP server framework |
| `flask-socketio` | WebSocket support for Flask |
| `pyautogui` | Programmatic mouse and keyboard control |
| `python-dotenv` | Load `.env` configuration file |
| `colorama` | Colored terminal output (cli.py) |

**Troubleshooting:**

- **Windows:** If `pip` is not recognized, use `py -m pip install -r requirements.txt`
- **Linux/macOS:** If you get a permission error, use `pip install --user -r requirements.txt` or create a virtual environment:
  ```bash
  python -m venv venv
  source venv/bin/activate  # Linux/macOS
  venv\Scripts\activate     # Windows
  pip install -r requirements.txt
  ```
- **Apple Silicon (M1/M2/M3):** `pyautogui` works natively. No special steps needed.

## Step 3: (Optional) Configure SMTP for Email Delivery

SMTP is used to email the tunnel URL to your phone. This solves the chicken-and-egg problem: you need the URL to connect, but you need to be connected to see the URL.

### 3.1. Create the .env file

```bash
cp .env.example .env
```

### 3.2. Edit .env with your SMTP credentials

Open `.env` in any text editor and fill in your settings.

**Gmail example:**

```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your.email@gmail.com
SMTP_PASSWORD=your-16-character-app-password
SMTP_FROM_EMAIL=your.email@gmail.com
SMTP_TO_EMAIL=your-phone-number@vtext.com
```

**Gmail App Password instructions:**

1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification if not already enabled
3. Go to https://myaccount.google.com/apppasswords
4. Select "Mail" and "Windows Computer" (or any)
5. Copy the 16-character password — use this in `.env`, not your regular password

**Other providers:**

| Provider | SMTP Host | Port | Notes |
|----------|-----------|------|-------|
| Gmail | smtp.gmail.com | 587 | Requires App Password |
| Outlook.com | smtp-mail.outlook.com | 587 | Microsoft account password |
| Yahoo Mail | smtp.mail.yahoo.com | 587 | App password recommended |
| ProtonMail | Requires ProtonMail Bridge | — | Not directly supported |

### 3.3. Test the email configuration

```bash
python email_service.py --test
```

If successful, you should receive a test email. If it fails, check your credentials and network connectivity.

### 3.4. SMS gateways (send URL as text message)

You can send the URL as an SMS text message using your carrier's email-to-SMS gateway:

| Carrier | Email-to-SMS Address |
|---------|---------------------|
| Verizon | `number@vtext.com` |
| T-Mobile | `number@tmomail.net` |
| AT&T | `number@txt.att.net` |
| Sprint | `number@messaging.sprintpcs.com` |
| Xfinity Mobile | `number@vtext.com` |
| Google Fi | `number@msg.fi.google.com` |
| US Cellular | `number@email.uscc.net` |
| Cricket | `number@mms.cricketwireless.net` |
| Boost Mobile | `number@myboostmobile.com` |

Set `SMTP_TO_EMAIL` to the appropriate gateway address. The SMS will arrive within a few seconds.

## Step 4: (Optional) Install cloudflared

cloudflared creates a secure tunnel from the public internet to your laptop, allowing you to connect from anywhere (different networks, cellular data, etc.).

### Windows

1. Download the Windows 64-bit MSI installer from: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
2. Run the installer
3. Verify: open a new terminal and type `cloudflared version`

### Linux (Debian/Ubuntu)

```bash
# Download the deb package
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb

# Install
sudo dpkg -i cloudflared-linux-amd64.deb

# Verify
cloudflared version
```

### Linux (RHEL/CentOS/Fedora)

```bash
sudo rpm -i https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-x86_64.rpm
cloudflared version
```

### macOS

```bash
brew install cloudflared
cloudflared version
```

## Step 5: Configure Windows Firewall (Windows Only)

If you are using Windows, you may need to allow inbound connections on port 5000:

```powershell
# Run as Administrator
netsh advfirewall firewall add rule name="Remote Mouse 5000" dir=in action=allow protocol=TCP localport=5000
```

This rule was already added if you used the setup script, but you can verify with:

```powershell
netsh advfirewall firewall show rule name="Remote Mouse 5000"
```

## Step 6: Start the Server

### Method A: CLI Control Panel (Recommended)

The CLI provides a live-updating terminal with all server events printed in color:

```bash
python cli.py
```

You will see the server start, and then a prompt `> ` where you can type commands:

```
+---------------------------------------+
|       Remote Mouse  v1.0              |
|       Terminal Control Panel          |
+---------------------------------------+
  Type 'help' for commands     'q' to quit
-----------------------------------------

  [19:30:22] * Server starting on port 5000...
  [19:30:22] * Local:  http://10.0.0.5:5000
```

### Method B: Direct Server

```bash
python server.py
```

### Method C: Launcher Scripts (with Cloudflare Tunnel)

**Windows:**

```powershell
.\scripts\start.ps1
```

**Linux/macOS:**

```bash
./scripts/start.sh
```

These scripts:
1. Check Python is installed
2. Install/update Python dependencies
3. Check for cloudflared
4. Start the Python server
5. Start the Cloudflare tunnel (if available)
6. Write the tunnel URL to `.tunnel_url`
7. Display connection info

## Step 7: Connect Your Phone

### Local Network (Same WiFi)

1. Find your laptop's IP address:
   - **Windows:** `ipconfig` (look for "IPv4 Address")
   - **Linux/macOS:** `ip addr` or `ifconfig`
2. Open your phone's browser and navigate to `http://<laptop-ip>:5000`
3. Example: `http://10.0.0.5:5000`

### Remote Access (Different Networks)

If you installed cloudflared and started it with the launcher script:

1. Check your phone's email/SMS — the tunnel URL was sent automatically
2. Tap the link in the email/SMS
3. The page loads and you are connected

### Verify Connection

Once the page loads, check the status bar at the top:
- **Green dot** with "Connected" — WebSocket is active, everything works
- **Gray dot** with "Disconnected" or "Reconnecting" — check the URL and network connectivity

## Step 8: Verify the Setup Works

1. On the touchpad, drag your finger — the cursor on your laptop should move
2. Tap the touchpad — a left click should register
3. Tap the "Right" button — a right click should register
4. Switch to the Media tab and try Play/Pause
5. Switch to the Link tab — verify the tunnel URL is displayed
6. If email is configured, send the URL to yourself and verify it arrives

## What to Do Next

- Read `docs/USAGE.md` for a detailed guide on all features
- Read `docs/CONFIGURATION.md` for advanced configuration options
- Read `docs/TROUBLESHOOTING.md` if you run into problems
