param([string]$Version = '2026.10.0')
$ErrorActionPreference = 'Stop'
if ($Version -notmatch '^\d{4}\.\d+\.\d+$') { throw 'Supply an official YYYY.M.N release tag.' }
if ($env:PROCESSOR_ARCHITECTURE -ne 'AMD64') { throw 'This installer is for Windows x64; use the official downloads for your platform.' }
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskDir = Join-Path $taskRoot '.local-tools\cloudflared'
$taskExe = Join-Path $taskDir 'cloudflared.exe'
if (Test-Path -LiteralPath $taskExe) {
    & $taskExe --version
    Write-Output 'Existing local binary preserved. Set CLOUDFLARED_PATH to use a different installation.'
    exit 0
}
Write-Output ('[' + (Get-Date -Format o) + '] Downloading official Cloudflare release ' + $Version)
$taskRelease = Invoke-RestMethod ('https://api.github.com/repos/cloudflare/cloudflared/releases/tags/' + $Version)
$taskAsset = $taskRelease.assets | Where-Object { $_.name -eq 'cloudflared-windows-amd64.exe' }
if (-not $taskAsset -or $taskAsset.digest -notmatch '^sha256:[0-9a-f]{64}$' -or
    $taskAsset.browser_download_url -notlike 'https://github.com/cloudflare/cloudflared/releases/download/*') {
    throw 'The official release has no verifiable Windows x64 asset.'
}
New-Item -ItemType Directory -Path $taskDir -Force | Out-Null
$taskDownload = Join-Path $taskDir ('cloudflared-' + $Version + '.download')
Invoke-WebRequest -Uri $taskAsset.browser_download_url -OutFile $taskDownload
$taskHash = (Get-FileHash -LiteralPath $taskDownload -Algorithm SHA256).Hash.ToLower()
if ('sha256:' + $taskHash -ne $taskAsset.digest) { throw 'Download hash differs from the official release. Nothing was installed.' }
Move-Item -LiteralPath $taskDownload -Destination $taskExe
& $taskExe --version
Write-Output ('[' + (Get-Date -Format o) + '] Official release SHA-256 verified: ' + $taskHash)
