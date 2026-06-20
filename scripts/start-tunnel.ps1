param([int]$Port = 0)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
$LogFile = "$ProjectRoot\tunnel.log"
$PortFile = "$ProjectRoot\.port"

if ($Port -eq 0 -and (Test-Path $PortFile)) {
  $Port = [int](Get-Content $PortFile -Raw).Trim()
}
if ($Port -eq 0) { $Port = 3000 }

Write-Host "TouchMorph - Cloudflare Tunnel" -ForegroundColor Cyan
Write-Host ""

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
  Write-Error "cloudflared not found. Install from: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
  exit 1
}

Write-Host "Starting tunnel to localhost:$Port ..." -ForegroundColor Yellow

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "cloudflared"
$psi.Arguments = "tunnel --url http://localhost:$Port"
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true

$proc = [System.Diagnostics.Process]::Start($psi)

$urlFound = $false
$timeout = 15
$elapsed = 0

while (-not $proc.HasExited -and $elapsed -lt $timeout) {
  Start-Sleep -Seconds 1
  $elapsed++

  if (-not $urlFound) {
    $output = $proc.StandardOutput.ReadToEnd() + $proc.StandardError.ReadToEnd()
    if ($output -match 'https://[a-z0-9-]+\.trycloudflare\.com') {
      $urlFound = $true
      $tunnelUrl = $matches[0]

      Write-Host ""
      Write-Host "╔════════════════════════════════════════════════╗" -ForegroundColor Green
      Write-Host "║  SECURE HTTPS TUNNEL ACTIVE                   ║" -ForegroundColor Green
      Write-Host "║                                              ║" -ForegroundColor Green
      Write-Host "║  $tunnelUrl" -ForegroundColor Cyan
      Write-Host "║                                              ║" -ForegroundColor Green
      Write-Host "╚════════════════════════════════════════════════╝" -ForegroundColor Green
      Write-Host ""

      try {
        python "$ProjectRoot\server\email_service.py" --send "$tunnelUrl"
        Write-Host "Email sent (if SMTP configured)." -ForegroundColor DarkGray
      } catch {
        Write-Host "Email service not available. URL printed above." -ForegroundColor Yellow
      }

      Write-Host "Press Ctrl+C to stop the tunnel." -ForegroundColor DarkGray
    }
  }
}

if (-not $urlFound) {
  Write-Warning "Could not detect tunnel URL. Check the log: $LogFile"
  $proc.StandardOutput.ReadToEnd() | Out-File $LogFile
  $proc.StandardError.ReadToEnd() | Out-File "${LogFile}.err"
}

$proc.WaitForExit()
