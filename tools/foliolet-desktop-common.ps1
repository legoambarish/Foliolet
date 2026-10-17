# Shared read-only checks used by the desktop launcher and its startup worker.
if ($PSVersionTable.PSVersion.Major -lt 6) {
    # A launcher opened from Python/PowerShell 7 can inherit only PS7 module paths.
    # Restore the built-in Windows modules for this process, without changing the user environment.
    $env:PSModulePath=(Join-Path $PSHOME 'Modules')+';'+(Join-Path $env:ProgramFiles 'WindowsPowerShell\Modules')+';'+$env:PSModulePath
}
$folioletRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$folioletData = Join-Path $folioletRoot '.local-data'
$folioletUrl = 'http://127.0.0.1:8008/'
$folioletHash = [Security.Cryptography.SHA256]::Create()
try { $folioletIdentity = [BitConverter]::ToString($folioletHash.ComputeHash([Text.Encoding]::UTF8.GetBytes($folioletRoot.ToLowerInvariant()))).Replace('-','').Substring(0,20) }
finally { $folioletHash.Dispose() }

function Get-FolioletPowerShell {
    $current=(Get-Process -Id $PID).Path
    if ([IO.Path]::GetFileName($current) -in @('pwsh.exe','powershell.exe')) { return $current }
    $candidate = Get-Command pwsh.exe -ErrorAction SilentlyContinue
    if ($candidate) { return $candidate.Source }
    return Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
}

function Assert-FolioletBranch {
    $branch = (git -C $folioletRoot branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0 -or ($branch -notlike 'feature/digilocker-assisted-intake*' -and $branch -ne 'feature/ps32-final-winning-audit-20261016-1645')) {
        throw 'Use the dedicated DigiLocker feature or PS32 audit checkout. No branch was changed.'
    }
}

function Assert-FolioletPath([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($folioletRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Launcher state must stay inside this feature checkout.' }
    $parent = [IO.Path]::GetDirectoryName($full)
    while ($parent -and $parent.Length -ge $folioletRoot.Length) {
        if ((Test-Path -LiteralPath $parent) -and ((Get-Item -LiteralPath $parent).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Launcher state cannot traverse a junction or symbolic link.' }
        $parent = [IO.Path]::GetDirectoryName($parent)
    }
    return $full
}

function Write-FolioletJson([string]$Path, $Value) {
    $full = Assert-FolioletPath $Path
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($full)) -Force | Out-Null
    $temp = Assert-FolioletPath ($full + '.' + $PID + '.tmp')
    [IO.File]::WriteAllText($temp, ($Value | ConvertTo-Json -Depth 8), (New-Object Text.UTF8Encoding($false)))
    for ($attempt=0; $attempt -lt 6; $attempt++) {
        try {
            if ([IO.File]::Exists($full)) { [IO.File]::Replace($temp, $full, [NullString]::Value) }
            else { [IO.File]::Move($temp, $full) }
            return
        } catch [IO.IOException] {
            if ($attempt -eq 5) { throw }
            Start-Sleep -Milliseconds 25
        }
    }
}

function Read-FolioletJson([string]$Path) {
    # Readers permit atomic replacement; a brief antivirus/writer lock is retried on the next UI tick.
    try {
        $share=[IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete
        $stream=New-Object IO.FileStream($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,$share)
        $reader=New-Object IO.StreamReader($stream)
        try { $text=$reader.ReadToEnd() } finally { $reader.Dispose(); $stream.Dispose() }
        return ConvertFrom-Json -InputObject $text
    } catch [IO.IOException] { return $null }
}

function Get-FolioletListener([int]$Port) {
    return @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

function Test-FolioletProcess($Entry) {
    if (-not $Entry -or $Entry.root -ne $folioletRoot) { return $false }
    $process = Get-Process -Id $Entry.pid -ErrorAction SilentlyContinue
    if (-not $process) { return $false }
    if ([math]::Abs(($process.StartTime.ToUniversalTime() - ([datetime]$Entry.started).ToUniversalTime()).TotalSeconds) -gt 1) { return $false }
    $command = Get-CimInstance Win32_Process -Filter "ProcessId=$($Entry.pid)"
    return $command.CommandLine -and $command.CommandLine.IndexOf($folioletRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0
}

function Test-FolioletListener($Listener, $Entry) {
    if (-not (Test-FolioletProcess $Entry)) { return $false }
    $currentId=[int]$Listener.OwningProcess
    for ($level=0; $level -lt 6; $level++) {
        if ($currentId -eq [int]$Entry.pid) { return $true }
        $process=Get-CimInstance Win32_Process -Filter "ProcessId=$currentId"
        if (-not $process -or -not $process.CommandLine -or $process.CommandLine.IndexOf($folioletRoot,[StringComparison]::OrdinalIgnoreCase) -lt 0) { return $false }
        $currentId=[int]$process.ParentProcessId
    }
    return $false
}

function Assert-FolioletOwnedPorts {
    $manifest = Join-Path $folioletData 'intake-processes.json'
    $entries = @()
    if (Test-Path -LiteralPath $manifest) { $entries = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json }
    foreach ($service in @(@{port=8548;name='intake-evm'}, @{port=8088;name='intake-spring'}, @{port=8008;name='intake-django'})) {
        foreach ($listener in (Get-FolioletListener $service.port)) {
            $entry = @($entries | Where-Object { $_.name -eq $service.name })
            if ($listener.LocalAddress -ne '127.0.0.1' -or $entry.Count -ne 1 -or -not (Test-FolioletListener $listener $entry[0])) { throw "Port $($service.port) belongs to another process. Close that application or use Foliolet's own Stop button. Nothing was stopped." }
        }
    }
    foreach ($listener in (Get-FolioletListener 55438)) {
        $manifest = Join-Path $folioletData 'intake-postgres.json'
        if (-not (Test-Path -LiteralPath $manifest)) { throw 'Database port 55438 is occupied without this checkout ownership record. Nothing was stopped.' }
        $pg = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
        $expected = Join-Path $folioletData 'postgres-intake'
        $command = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
        $pidFile = Join-Path $expected 'postmaster.pid'
        if ($listener.LocalAddress -ne '127.0.0.1' -or $pg.root -ne $folioletRoot -or [IO.Path]::GetFullPath($pg.data) -ne $expected -or $command.Name -ne 'postgres.exe' -or -not $command.CommandLine -or -not $command.CommandLine.Replace('/','\').Contains($expected) -or -not (Test-Path -LiteralPath $pidFile) -or [int](Get-Content -LiteralPath $pidFile -TotalCount 1) -ne $listener.OwningProcess) { throw 'Database port 55438 belongs to another process. Nothing was stopped.' }
    }
}

function Get-FolioletModel([string]$Url) {
    try {
        # WebRequest defaults do not use application proxy settings for this numeric loopback call.
        $status = Invoke-RestMethod ($Url + '/api/status') -TimeoutSec 3
        if (-not $status.cloud.disabled) { return $false }
        $models = (Invoke-RestMethod ($Url + '/api/tags') -TimeoutSec 3).models
        return @($models | Where-Object { $_.name -eq 'qwen3:4b-instruct' -and $_.size -gt 0 -and $_.size -lt 5000000000 }).Count -eq 1
    } catch { return $false }
}

function Test-FolioletReady {
    foreach ($port in @(55438,8548,8088,8008)) { if (-not @(Get-FolioletListener $port).Count) { return $false } }
    try {
        $chain = Invoke-RestMethod 'http://127.0.0.1:8548' -Method Post -ContentType 'application/json' -Body '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' -TimeoutSec 4
        if ($chain.result -ne '0x539') { return $false }
        $springReady = $false
        try { $null = Invoke-WebRequest 'http://127.0.0.1:8088/api/wallet' -UseBasicParsing -TimeoutSec 4 }
        catch { if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -in @(401,403)) { $springReady = $true } }
        if (-not $springReady) { return $false }
        $page = Invoke-WebRequest ($folioletUrl + 'login/') -UseBasicParsing -TimeoutSec 5
        return [int]$page.StatusCode -eq 200 -and $page.Content -match 'csrfmiddlewaretoken' -and $page.Content -match 'Foliolet'
    } catch { return $false }
}
