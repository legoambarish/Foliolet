param([string]$PairingFile)
$ErrorActionPreference='Stop'
$intakeRoot=Split-Path -Parent $PSScriptRoot
if (-not $PairingFile) {
    $intakeLatest=Get-ChildItem -LiteralPath (Join-Path $env:USERPROFILE 'Downloads') -File |
        Where-Object { $_.Name -match '^foliolet-intake(?: \(\d+\))?\.json$' } |
        Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    if ($intakeLatest) { $PairingFile=$intakeLatest.FullName }
}
if (-not $PairingFile -or -not (Test-Path -LiteralPath $PairingFile -PathType Leaf)) {
    Add-Type -AssemblyName System.Windows.Forms
    $intakePicker=New-Object System.Windows.Forms.OpenFileDialog
    $intakePicker.Title='Select the Foliolet pairing file you downloaded'
    $intakePicker.Filter='Foliolet pairing file (*.json)|*.json'
    if ($intakePicker.ShowDialog() -ne 'OK') { return }
    $PairingFile=$intakePicker.FileName
}
$intakeConfig=Get-Content -LiteralPath $PairingFile -Raw | ConvertFrom-Json
if ($intakeConfig.sessionId -notmatch '^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$') { throw 'Invalid pairing file' }
$intakeExpiry=if ($intakeConfig.expiresAt -is [DateTime]) { [DateTimeOffset]::new($intakeConfig.expiresAt) } else { [DateTimeOffset]::Parse($intakeConfig.expiresAt) }
if ($intakeExpiry -le [DateTimeOffset]::UtcNow) { throw 'This pairing expired. Enable a new folder intake session in Foliolet and retry.' }
$intakeState=Join-Path $intakeRoot ('.local-data\intake\'+$intakeConfig.sessionId)
New-Item -ItemType Directory -Path $intakeState -Force | Out-Null
$intakeIdentity=[Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $intakeState /inheritance:r /grant:r "${intakeIdentity}:(OI)(CI)F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not restrict companion state permissions' }
$intakeConfigCopy=Join-Path $intakeState 'pairing.json'
if (-not (Test-Path -LiteralPath $intakeConfigCopy)) { Copy-Item -LiteralPath $PairingFile -Destination $intakeConfigCopy }
& (Join-Path $intakeRoot '.venv\Scripts\python.exe') (Join-Path $intakeRoot 'tools\local-watcher\intake.py') --config $intakeConfigCopy --state-dir $intakeState
if ($LASTEXITCODE -ne 0) { throw 'The companion stopped. Re-arm an expired/revoked session in Foliolet or retry the same pairing before expiry.' }
