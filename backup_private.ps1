# Pack references/private/ into a timestamped archive (Windows, uses built-in bsdtar).
# Encryption needs openssl (Git Bash / Linux / macOS): use backup_private.sh --encrypt there.
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$privateDir = Join-Path $projectRoot "references\private"
$backupDir = Join-Path $projectRoot "backups"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$archive = Join-Path $backupDir "private-$stamp.tar.gz"

if (-not (Test-Path $privateDir)) {
    Write-Error "error: $privateDir not found"
    exit 1
}

New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
tar -czf $archive -C (Join-Path $projectRoot "references") private
Write-Output "Created: $archive"
Write-Output "Copy the archive to cloud storage or another machine; backups/ stays out of git."
