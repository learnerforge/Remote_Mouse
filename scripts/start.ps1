$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "=== Remote Mouse Launcher ===" -ForegroundColor Cyan

# 1. Check Python
try {
  $pyVersion = python --version 2>&1
  Write-Host "[OK] $pyVersion" -ForegroundColor Green
} catch {
  Write-Host "[FAIL] Python not found. Install Python 3.10+" -ForegroundColor Red
  exit 1
}

# 2. Install deps
Write-Host "[...] Installing dependencies..." -ForegroundColor Yellow
python -m pip install -r requirements.txt --quiet 2>&1 | Out-Null

# 3. Check cloudflared
$hasCloudflared = $false
try {
  $cfVersion = cloudflared version 2>&1
  Write-Host "[OK] cloudflared: $cfVersion" -ForegroundColor Green
  $hasCloudflared = $true
} catch {
  Write-Host "[WARN] cloudflared not found. Install from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/" -ForegroundColor Yellow
  Write-Host "[WARN] Falling back to local network only." -ForegroundColor Yellow
}

# 4. Start Python server
Write-Host "[...] Starting server..." -ForegroundColor Yellow
$serverProcess = Start-Process -FilePath "python" -ArgumentList "src\server.py" -NoNewWindow -PassThru -RedirectStandardOutput "$ProjectRoot\server.log" -RedirectStandardError "$ProjectRoot\server.log"

Start-Sleep -Seconds 2

# Check if server is running
$serverRunning = Get-Process -Id $serverProcess.Id -ErrorAction SilentlyContinue
if (-not $serverRunning) {
  Write-Host "[FAIL] Server failed to start. Check server.log" -ForegroundColor Red
  exit 1
}
Write-Host "[OK] Server running on port 5000" -ForegroundColor Green

# 5. Start tunnel (if cloudflared available)
$tunnelUrl = ""
if ($hasCloudflared) {
  Write-Host "[...] Starting Cloudflare tunnel..." -ForegroundColor Yellow

  $tunnelLog = "$ProjectRoot\tunnel.log"
  $tunnelProcess = Start-Process -FilePath "cloudflared" -ArgumentList @("tunnel", "--url", "http://localhost:5000", "--logfile", $tunnelLog) -NoNewWindow -PassThru

  Write-Host "[...] Waiting for tunnel URL..." -ForegroundColor Yellow
  $urlFound = $false
  for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path $tunnelLog) {
      $log = Get-Content $tunnelLog -Raw
      if ($log -match 'https://[a-zA-Z0-9-]+\.trycloudflare\.com') {
        $tunnelUrl = $matches[0]
        $urlFound = $true
        break
      }
    }
  }

  if ($urlFound) {
    Write-Host "[OK] Tunnel URL: $tunnelUrl" -ForegroundColor Green
    # Write to file so server can expose it via API
    $tunnelUrl | Out-File -FilePath "$ProjectRoot\.tunnel_url" -Encoding utf8 -Force
  } else {
    Write-Host "[WARN] Could not extract tunnel URL from logs." -ForegroundColor Yellow
  }
}

# 6. Print access info
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Remote Mouse is running!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

if ($tunnelUrl) {
  Write-Host "  Internet:    $tunnelUrl" -ForegroundColor White
}

# Get local IP
$localIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike '*Loopback*' -and $_.IPAddress -notlike '169.*' }).IPAddress | Select-Object -First 1
if ($localIp) {
  Write-Host "  Local:       http://${localIp}:5000" -ForegroundColor White
}
Write-Host "  Local:       http://127.0.0.1:5000" -ForegroundColor White

Write-Host ""
Write-Host "Open the URL on your phone to start controlling." -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C in the server terminal to stop." -ForegroundColor Yellow
Write-Host ""

# Keep tunnel process alive
if ($hasCloudflared) {
  try {
    $tunnelProcess | Wait-Process
  } catch {
    # Tunnel process ended
  }
} else {
  # Keep script alive
  Write-Host "Waiting... Press Ctrl+C to stop." -ForegroundColor Gray
  try {
    $serverProcess | Wait-Process
  } catch {}
}
