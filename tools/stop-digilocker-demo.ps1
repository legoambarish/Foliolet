$ErrorActionPreference='Stop'
$intakeRoot=(Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
$intakeManifest=Join-Path $intakeRoot '.local-data\intake-processes.json'
function Stop-IntakeChildren([int]$ParentId) {
    foreach ($intakeChild in @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$ParentId")) {
        if ($intakeChild.Name -eq 'conhost.exe') { continue } # Windows tears down its console with the owned parent.
        if (-not $intakeChild.CommandLine -or -not $intakeChild.CommandLine.Contains($intakeRoot)) { throw 'A child process is outside this worktree; stop refused.' }
        Stop-IntakeChildren $intakeChild.ProcessId
        Stop-Process -Id $intakeChild.ProcessId -ErrorAction SilentlyContinue
    }
}
$intakeEntries=@()
foreach ($intakeFile in @($intakeManifest,(Join-Path $intakeRoot '.local-data\intake-model-process.json'))) {
    if (Test-Path -LiteralPath $intakeFile) { $intakeParsed=Get-Content -LiteralPath $intakeFile -Raw | ConvertFrom-Json; $intakeEntries+=@($intakeParsed) }
}
if ($intakeEntries.Count) {
    foreach ($intakeEntry in $intakeEntries) {
        if ($intakeEntry.root -ne $intakeRoot) { throw 'Managed-process workspace mismatch; no further processes stopped.' }
        $intakeProcess=Get-Process -Id $intakeEntry.pid -ErrorAction SilentlyContinue
        if (-not $intakeProcess) { continue }
        $intakeStarted=([datetime]$intakeEntry.started).ToUniversalTime()
        if ([math]::Abs(($intakeProcess.StartTime.ToUniversalTime()-$intakeStarted).TotalSeconds) -gt 1) { throw 'PID was reused; stop refused.' }
        $intakeCim=Get-CimInstance Win32_Process -Filter "ProcessId=$($intakeEntry.pid)"
        if (-not $intakeCim.CommandLine.Contains($intakeRoot)) { throw 'Process command does not belong to this worktree; stop refused.' }
        Stop-IntakeChildren $intakeEntry.pid
        Stop-Process -Id $intakeEntry.pid -ErrorAction SilentlyContinue
        Write-Host "Stopped managed $($intakeEntry.name)."
    }
}
$intakePgManifest=Join-Path $intakeRoot '.local-data\intake-postgres.json'
if (Test-Path -LiteralPath $intakePgManifest) {
    $intakePg=Get-Content -LiteralPath $intakePgManifest -Raw | ConvertFrom-Json
    $intakeExpected=Join-Path $intakeRoot '.local-data\postgres-intake'
    if ($intakePg.root -ne $intakeRoot -or [IO.Path]::GetFullPath($intakePg.data) -ne $intakeExpected) { throw 'PostgreSQL path mismatch; stop refused.' }
    & (Join-Path $intakePg.bin 'pg_ctl.exe') -D $intakeExpected status | Out-Null
    if ($LASTEXITCODE -eq 0) { & (Join-Path $intakePg.bin 'pg_ctl.exe') -D $intakeExpected -w stop }
}
Write-Host 'Managed demo stopped. All databases, originals, models and keys are retained.'
