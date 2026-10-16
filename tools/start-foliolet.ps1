param([switch]$CheckOnly, [switch]$Stop, [string]$StatusPath)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'foliolet-desktop-common.ps1')
if (-not $StatusPath) { $StatusPath = Join-Path $folioletData 'desktop-status.json' }
$StatusPath = Assert-FolioletPath $StatusPath
$mutex = New-Object Threading.Mutex($false, ('Local\FolioletStart-' + $folioletIdentity))
$locked = $false
function Status([string]$State, [string]$Message, [int]$Progress) {
    Write-FolioletJson $StatusPath @{state=$State;message=$Message;progress=$Progress;url=$folioletUrl;updated=(Get-Date).ToUniversalTime().ToString('o');worker=$PID}
    Write-Output ('[' + (Get-Date -Format HH:mm:ss) + '] ' + $Message)
}
function Run-Step([string]$Name, [string]$Exe, [string[]]$Arguments, [int]$Seconds=300) {
    $log = Assert-FolioletPath (Join-Path $folioletData ('desktop-' + $Name + '.stdout.log'))
    $errorLog = Assert-FolioletPath (Join-Path $folioletData ('desktop-' + $Name + '.stderr.log'))
    $quoted = @($Arguments | ForEach-Object { '"' + ($_ -replace '"','\"') + '"' })
    $process = Start-Process -FilePath $Exe -ArgumentList $quoted -WorkingDirectory $folioletRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput $log -RedirectStandardError $errorLog
    # Keep the native handle open so Windows PowerShell retains a fast child's exit code.
    $null=$process.Handle
    $deadline = (Get-Date).AddSeconds($Seconds)
    $heartbeat = Get-Date
    while (-not $process.WaitForExit(500)) {
        if ((Get-Date) -gt $deadline) { throw "$Name took too long. Its diagnostic logs are in .local-data; no databases or keys were reset." }
        if (((Get-Date)-$heartbeat).TotalSeconds -ge 10) { Write-Output ('[' + (Get-Date -Format HH:mm:ss) + '] Still working: ' + $Name); $heartbeat=Get-Date }
    }
    $process.Refresh()
    if ($process.ExitCode -ne 0) { throw "$Name could not finish. Open logs for desktop-$Name.stderr.log and desktop-$Name.stdout.log. Your saved documents and keys are retained." }
}
function Run-Script([string]$Name, [string]$File, [string[]]$Arguments, [int]$Seconds=300) {
    Run-Step $Name (Get-FolioletPowerShell) (@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(Join-Path $PSScriptRoot $File)) + $Arguments) $Seconds
}
try {
    try { $locked=$mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $locked=$true }
    if (-not $locked) { throw 'Foliolet is already starting or stopping. Wait for its existing launcher window.' }
    if ((git -C $folioletRoot branch --show-current).Trim() -ne 'feature/digilocker-assisted-intake') { throw 'This launcher belongs to feature/digilocker-assisted-intake. No branch was changed.' }
    Status 'starting' 'Checking the local services...' 5
    Assert-FolioletOwnedPorts
    if ($CheckOnly) {
        if (-not (Test-FolioletReady)) { throw 'Foliolet is not ready yet.' }
        Status 'ready' 'Foliolet is running.' 100
        exit 0
    }
    if ($Stop) {
        Status 'stopping' 'Stopping this Foliolet instance...' 20
        Run-Script 'stop' 'stop-digilocker-demo.ps1' @() 120
        Status 'stopped' 'Foliolet is stopped. Your documents and settings are saved.' 0
        exit 0
    }
    Status 'starting' 'Finding the installed local tools...' 12
    foreach ($tool in @('java.exe','node.exe','git.exe')) { if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "Required tool $tool is missing. Install Java 17, Node.js and Git, then click Foliolet again." } }
    $candidates = @($folioletRoot, (Join-Path (Split-Path -Parent $folioletRoot) 'Foliolet-testcloudflare'))
    $runtimeRoot = $null
    foreach ($candidate in $candidates) {
        if ((Test-Path -LiteralPath (Join-Path $candidate '.local-tools\postgres\bin\pg_ctl.exe')) -and (Test-Path -LiteralPath (Join-Path $candidate '.local-tools\ocr\Library\bin\tesseract.exe'))) { $runtimeRoot=$candidate; break }
    }
    if (-not $runtimeRoot) { throw 'The portable PostgreSQL and OCR runtime was not found in this checkout or Foliolet-testcloudflare. Restore that retained runtime folder, then click Foliolet again.' }
    $python = Join-Path $folioletRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        Status 'starting' 'Preparing Foliolet Python...' 18
        $systemPython = Get-Command python.exe -ErrorAction SilentlyContinue
        if (-not $systemPython) { throw 'Python 3.12 or newer is required. Install Python and click Foliolet again.' }
        Run-Step 'python-setup' $systemPython.Source @('-m','venv',(Join-Path $folioletRoot '.venv')) 180
    }
    $requirements = @('django-service/requirements.txt','tools/requirements-dev.txt')
    $requirementsHash = ($requirements | ForEach-Object { (Get-FileHash -LiteralPath (Join-Path $folioletRoot $_) -Algorithm SHA256).Hash }) -join ':'
    $dependencyRecord = Join-Path $folioletData 'desktop-python.json'
    $previousHash = $null
    if (Test-Path -LiteralPath $dependencyRecord) { $previousHash=(Get-Content -LiteralPath $dependencyRecord -Raw | ConvertFrom-Json).requirements }
    $modulesReady = $false
    try { Run-Step 'python-check' $python @('-c','import django,requests,watchdog,psycopg,Crypto,waitress; from importlib.metadata import version; assert version("Django")=="6.1"') 30; $modulesReady=$true } catch { }
    if (-not $modulesReady -or ($previousHash -and $previousHash -ne $requirementsHash)) {
        Status 'starting' 'Installing the project Python dependencies...' 22
        Run-Step 'python-dependencies' $python @('-m','pip','install','-r',(Join-Path $folioletRoot $requirements[0]),'-r',(Join-Path $folioletRoot $requirements[1])) 600
    }
    Write-FolioletJson $dependencyRecord @{requirements=$requirementsHash}
    $env:NODE_PATH=(Join-Path $runtimeRoot 'spring-boot-service\node_modules') + ';' + (Join-Path $runtimeRoot 'node_modules')
    try { Run-Step 'node-check' (Get-Command node.exe).Source @('-e','for(const n of ["ethers","ganache","solc","qrcode-generator"]) require(n)') 30 }
    catch {
        Status 'starting' 'Preparing the local document-proof tools...' 27
        Run-Step 'node-root-setup' (Get-FolioletPowerShell) @('-NoProfile','-Command',('Set-Location -LiteralPath ''' + $folioletRoot.Replace("'","''") + '''; & npm.cmd ci --no-audit --no-fund; exit $LASTEXITCODE')) 600
        Run-Step 'node-contract-setup' (Get-FolioletPowerShell) @('-NoProfile','-Command',('Set-Location -LiteralPath ''' + $folioletRoot.Replace("'","''") + '''; & npm.cmd ci --prefix spring-boot-service --no-audit --no-fund; exit $LASTEXITCODE')) 600
        # PostgreSQL/OCR still come from the retained runtime. Include this checkout's newly installed packages.
        $env:NODE_PATH=(Join-Path $folioletRoot 'spring-boot-service\node_modules') + ';' + (Join-Path $folioletRoot 'node_modules') + ';' + $env:NODE_PATH
    }
    $jar=Join-Path $folioletRoot 'spring-boot-service\target\dms-0.0.1-SNAPSHOT.jar'
    $sources=@(Get-ChildItem -LiteralPath (Join-Path $folioletRoot 'spring-boot-service\src\main') -Recurse -File | Where-Object { $_.Name -notin @('application.properties','application.yaml') }) + @(Get-Item -LiteralPath (Join-Path $folioletRoot 'spring-boot-service\pom.xml'))
    $needsBuild=-not (Test-Path -LiteralPath $jar)
    if (-not $needsBuild) { $jarTime=(Get-Item -LiteralPath $jar).LastWriteTimeUtc; $needsBuild=@($sources | Where-Object { $_.LastWriteTimeUtc -gt $jarTime }).Count -gt 0 }
    $ready=Test-FolioletReady
    $activeRuntime=Join-Path $folioletData 'intake-runtime.json'
    $activeModel=$null
    if (Test-Path -LiteralPath $activeRuntime) {
        $runtime=Get-Content -LiteralPath $activeRuntime -Raw | ConvertFrom-Json
        if ($runtime.root -eq $folioletRoot -and $runtime.modelUrl -in @('http://127.0.0.1:11444','http://127.0.0.1:11434')) { $activeModel=$runtime.modelUrl }
    }
    if ($ready -and -not $needsBuild -and $activeModel -and (Get-FolioletModel $activeModel)) {
        Status 'ready' 'Foliolet is already running. Opening your workspace...' 100
        exit 0
    }
    if (@(Get-FolioletListener 11444).Count -and -not (Get-FolioletModel 'http://127.0.0.1:11444')) { throw 'The local assistant port 11444 is occupied by an unavailable or incompatible service. No services were stopped.' }
    # Recover a partial start only after every occupied application port passed ownership checks.
    if (@(Get-FolioletListener 55438).Count -or @(Get-FolioletListener 8548).Count -or @(Get-FolioletListener 8088).Count -or @(Get-FolioletListener 8008).Count) {
        Status 'starting' 'Resuming the saved Foliolet instance...' 32
        Run-Script 'stop' 'stop-digilocker-demo.ps1' @() 120
    }
    if ($needsBuild) {
        Status 'starting' 'Building Foliolet for this checkout. The first launch can take a few minutes...' 40
        Run-Step 'build' (Get-FolioletPowerShell) @('-NoProfile','-Command',('Set-Location -LiteralPath ''' + $folioletRoot.Replace("'","''") + '''; & .\spring-boot-service\mvnw.cmd -f spring-boot-service/pom.xml -B -DskipTests package; exit $LASTEXITCODE')) 900
    }
    Status 'starting' 'Starting the local document assistant...' 60
    $modelUrl = 'http://127.0.0.1:11444'
    if (-not (Get-FolioletModel $modelUrl)) {
        if (Get-FolioletModel 'http://127.0.0.1:11434') { $modelUrl='http://127.0.0.1:11434' }
        else {
            if (@(Get-FolioletListener 11444).Count) { throw 'The local assistant port 11444 is occupied by an unavailable or incompatible service. Nothing was stopped.' }
            Run-Script 'model' 'start-digilocker-model.ps1' @('-RuntimeRoot',$runtimeRoot) 300
            if (-not (Get-FolioletModel $modelUrl)) { throw 'The local assistant did not pass its offline-model readiness checks.' }
        }
    }
    Status 'starting' 'Starting the database and Foliolet services...' 75
    Run-Script 'services' 'start-digilocker-demo.ps1' @('-RuntimeRoot',$runtimeRoot,'-SkipBuild','-OllamaUrl',$modelUrl) 360
    Status 'starting' 'Checking Foliolet before opening the browser...' 95
    Assert-FolioletOwnedPorts
    if (-not (Test-FolioletReady)) { throw 'The services started but Foliolet is not ready. Open logs, then click Retry.' }
    Status 'ready' 'Foliolet is ready.' 100
} catch {
    Status 'error' $_.Exception.Message 0
    exit 1
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
