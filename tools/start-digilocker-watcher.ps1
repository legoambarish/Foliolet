param([string]$PairingFile, [switch]$Background, [switch]$Resume)
$ErrorActionPreference='Stop'
$intakeRoot=Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'foliolet-desktop-common.ps1')
$intakeWatcherManifest=Join-Path $intakeRoot '.local-data\intake-watcher-process.json'
$intakeWatcherSetting=Join-Path $intakeRoot '.local-data\intake-watcher.json'
if ($Resume) {
    if (-not (Test-Path -LiteralPath $intakeWatcherSetting)) { return }
    $intakeSaved=Get-Content -LiteralPath $intakeWatcherSetting -Raw | ConvertFrom-Json
    if ($intakeSaved.root -ne $intakeRoot) { throw 'Saved watcher belongs to a different checkout' }
    $PairingFile=Assert-FolioletPath $intakeSaved.pairingFile
    $Background=$true
}
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
if ($intakeConfig.expiresAt) {
    $intakeExpiry=if ($intakeConfig.expiresAt -is [DateTime]) { [DateTimeOffset]::new($intakeConfig.expiresAt) } else { [DateTimeOffset]::Parse($intakeConfig.expiresAt) }
    if ($intakeExpiry -le [DateTimeOffset]::UtcNow) { throw 'This pairing expired. Enable a new folder intake session in Foliolet and retry.' }
} elseif ($intakeConfig.lifetime -ne 'app') { throw 'Pairing must specify app lifetime or a valid expiry' }
if ($intakeConfig.apiUrl -cne "http://127.0.0.1:$($folioletPorts.api)") { throw "Pairing must use this checkout loopback API on $($folioletPorts.api)" }
Assert-FolioletOwnedPorts
$intakeAppArguments=@()
# Windows PowerShell 5.1 emits a parsed JSON array as one pipeline object.
# Assign first so filtering enumerates the individual service records on 5.1 and 7.
$intakeAppManifest=Get-Content -LiteralPath (Join-Path $intakeRoot '.local-data\intake-processes.json') -Raw | ConvertFrom-Json
$intakeAppEntries=@($intakeAppManifest | Where-Object { $_.name -in @('intake-spring','intake-django') })
if ($intakeAppEntries.Count -ne 2) { throw 'Start Foliolet before enabling its watcher' }
foreach ($intakeEntry in $intakeAppEntries) {
    $intakeApp=Get-Process -Id $intakeEntry.pid -ErrorAction Stop
    $intakeCim=Get-CimInstance Win32_Process -Filter "ProcessId=$($intakeEntry.pid)"
    if ($intakeEntry.root -ne $intakeRoot -or [math]::Abs(($intakeApp.StartTime.ToUniversalTime()-([datetime]$intakeEntry.started).ToUniversalTime()).TotalSeconds) -gt 1 -or -not $intakeCim.CommandLine.Contains($intakeRoot)) { throw 'Foliolet process ownership mismatch; watcher refused' }
    $intakeAppArguments+=@('--app-pid',[string]$intakeEntry.pid)
}
$intakeState=Join-Path $intakeRoot ('.local-data\intake\'+$intakeConfig.sessionId)
New-Item -ItemType Directory -Path $intakeState -Force | Out-Null
$intakeIdentity=[Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $intakeState /inheritance:r /grant:r "${intakeIdentity}:(OI)(CI)F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not restrict companion state permissions' }
$intakeConfigCopy=Join-Path $intakeState 'pairing.json'
if (-not (Test-Path -LiteralPath $intakeConfigCopy)) { Copy-Item -LiteralPath $PairingFile -Destination $intakeConfigCopy }
$intakePython=Join-Path $intakeRoot '.venv\Scripts\python.exe'
$intakeArguments=@((Join-Path $intakeRoot 'tools\local-watcher\intake.py'),'--config',$intakeConfigCopy,'--state-dir',$intakeState)+$intakeAppArguments
if (-not $Background) {
    & $intakePython @intakeArguments
    if ($LASTEXITCODE -ne 0) { throw 'The companion stopped. Re-enable folder intake if its pairing was stopped or expired.' }
    return
}
$intakeMutex=New-Object Threading.Mutex($false,('Local\FolioletWatcher-'+$folioletIdentity))
$intakeLocked=$false
try {
    try { $intakeLocked=$intakeMutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $intakeLocked=$true }
    if (-not $intakeLocked) { throw 'The watcher is already starting' }
    if (Test-Path -LiteralPath $intakeWatcherManifest) {
        $intakePrior=Get-Content -LiteralPath $intakeWatcherManifest -Raw | ConvertFrom-Json
        $intakeProcess=Get-Process -Id $intakePrior.pid -ErrorAction SilentlyContinue
        if ($intakeProcess) {
            $intakeCim=Get-CimInstance Win32_Process -Filter "ProcessId=$($intakePrior.pid)"
            if ($intakePrior.root -ne $intakeRoot -or [math]::Abs(($intakeProcess.StartTime.ToUniversalTime()-([datetime]$intakePrior.started).ToUniversalTime()).TotalSeconds) -gt 1 -or -not $intakeCim.CommandLine.Contains($intakeConfigCopy)) { throw 'An existing watcher process does not match this pairing; no process stopped' }
            Write-Output ('Watcher already running: '+$intakeConfig.folder)
            return
        }
    }
    $intakeOut=Join-Path $intakeState 'watcher.stdout.log'
    $intakeErr=Join-Path $intakeState 'watcher.stderr.log'
    $intakeQuoted=@($intakeArguments | ForEach-Object { '"'+($_ -replace '"','\"')+'"' })
    $intakeProcess=Start-Process -FilePath $intakePython -ArgumentList $intakeQuoted -WorkingDirectory $intakeRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput $intakeOut -RedirectStandardError $intakeErr
    Write-FolioletJson $intakeWatcherManifest @{name='intake-watcher';root=$intakeRoot;pid=$intakeProcess.Id;started=$intakeProcess.StartTime.ToUniversalTime().ToString('o')}
    $intakeDeadline=(Get-Date).AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 300
        $intakeProcess.Refresh()
        if ($intakeProcess.HasExited) {
            if ($Resume) { Write-Output 'Watcher pairing is no longer active. Enable folder intake to watch again.'; return }
            throw 'Watcher could not connect. Check its private state logs or enable a new pairing.'
        }
        $intakeConnected=(Get-Content -LiteralPath $intakeOut -Raw -ErrorAction SilentlyContinue) -match 'Intake active:'
    } while (-not $intakeConnected -and (Get-Date) -lt $intakeDeadline)
    if (-not $intakeConnected) { throw 'Watcher has not connected yet. Inspect its private state logs.' }
    if (-not $intakeConfig.expiresAt) { Write-FolioletJson $intakeWatcherSetting @{root=$intakeRoot;pairingFile=$intakeConfigCopy} }
    Write-Output ('Watcher connected while Foliolet is running: '+$intakeConfig.folder)
} finally {
    if ($intakeLocked) { $intakeMutex.ReleaseMutex() }
    $intakeMutex.Dispose()
}
