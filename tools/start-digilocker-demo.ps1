param([string]$RuntimeRoot, [switch]$SkipBuild, [string]$OllamaUrl='http://127.0.0.1:11434', [ValidateRange(512,4096)][int]$MaxHeapMb=768, [ValidateRange(1024,65535)][int]$PgPort=55438, [ValidateRange(1024,65535)][int]$EvmPort=8548, [ValidateRange(1024,65535)][int]$ApiPort=8088, [ValidateRange(1024,65535)][int]$UiPort=8008)
$ErrorActionPreference = 'Stop'
$intakeModelOrigin=[uri]$OllamaUrl
if ($intakeModelOrigin.Scheme -ne 'http' -or $intakeModelOrigin.Host -notin @('127.0.0.1','::1','[::1]') -or $intakeModelOrigin.Port -lt 1 -or $intakeModelOrigin.UserInfo -or $intakeModelOrigin.Query -or $intakeModelOrigin.Fragment -or $intakeModelOrigin.AbsolutePath -ne '/') { throw 'Use a numeric loopback HTTP Ollama origin with an explicit port.' }
$intakeRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
. (Join-Path $PSScriptRoot 'foliolet-desktop-common.ps1')
Assert-FolioletBranch
# Explicit command-line ports win; otherwise retain this checkout's saved ports.
foreach ($portSetting in @(@{arg='PgPort';key='pg'},@{arg='EvmPort';key='evm'},@{arg='ApiPort';key='api'},@{arg='UiPort';key='ui'})) {
    if ($PSBoundParameters.ContainsKey($portSetting.arg)) { $folioletPorts.($portSetting.key) = Get-Variable -Name $portSetting.arg -ValueOnly }
    else { Set-Variable -Name $portSetting.arg -Value $folioletPorts.($portSetting.key) }
}
Assert-FolioletPorts $folioletPorts
if (-not $RuntimeRoot) { $RuntimeRoot = $intakeRoot }
$RuntimeRoot = (Resolve-Path -LiteralPath $RuntimeRoot).Path
$intakePython = Join-Path $intakeRoot '.venv\Scripts\python.exe'
$intakePgBin = Join-Path $RuntimeRoot '.local-tools\postgres\bin'
$intakeOcr = Join-Path $RuntimeRoot '.local-tools\ocr\Library\bin\tesseract.exe'
foreach ($intakeRequired in @($intakePython, (Join-Path $intakePgBin 'pg_ctl.exe'))) {
    if (-not (Test-Path -LiteralPath $intakeRequired)) { throw "Missing runtime prerequisite: $intakeRequired. Follow the intake runbook." }
}
$intakeData = Join-Path $intakeRoot '.local-data'
New-Item -ItemType Directory -Path $intakeData -Force | Out-Null
$intakeManifest = Join-Path $intakeData 'intake-processes.json'
foreach ($intakePort in @($PgPort, $EvmPort, $ApiPort, $UiPort)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $intakePort -ErrorAction SilentlyContinue) { throw "Port $intakePort is already in use. No process was stopped or reused." }
}
# Persist before starting any process so partial startup is recoverable on the same ports.
Write-FolioletJson (Join-Path $intakeData 'intake-runtime.json') @{root=$intakeRoot;runtimeRoot=$RuntimeRoot;modelUrl=$OllamaUrl;ports=$folioletPorts}
function Intake-Status([string]$Message) { Write-Host ('[' + (Get-Date -Format 'HH:mm:ss') + '] ' + $Message) }
function Intake-Wait([int]$Port, [int]$Seconds=60) {
    $intakeDeadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $intakeDeadline) {
        if (Get-NetTCPConnection -State Listen -LocalAddress '127.0.0.1' -LocalPort $Port -ErrorAction SilentlyContinue) { return }
        Intake-Status "Waiting for loopback port $Port..."
        Start-Sleep -Seconds 3
    }
    throw "Service on port $Port did not become ready. Inspect this worktree's .local-data logs."
}
$intakeProcesses = @()
function Intake-Launch([string]$Name, [string]$Executable, [string[]]$Arguments, [string]$WorkingDirectory) {
    Intake-Status "Starting $Name"
    $intakeQuotedArguments=@($Arguments | ForEach-Object { '"'+($_ -replace '"','\"')+'"' })
    $intakeProcess = Start-Process -FilePath $Executable -ArgumentList $intakeQuotedArguments -WorkingDirectory $WorkingDirectory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $intakeData "$Name.stdout.log") -RedirectStandardError (Join-Path $intakeData "$Name.stderr.log")
    $script:intakeProcesses += @{name=$Name; pid=$intakeProcess.Id; started=$intakeProcess.StartTime.ToUniversalTime().ToString('o'); root=$intakeRoot}
    $script:intakeProcesses | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $intakeManifest -Encoding utf8
}
if (-not $SkipBuild) {
    Intake-Status 'Building the current feature source'
    & (Join-Path $intakeRoot 'spring-boot-service\mvnw.cmd') -f (Join-Path $intakeRoot 'spring-boot-service\pom.xml') -B -DskipTests package
    if ($LASTEXITCODE -ne 0) { throw 'Feature build failed' }
}
$intakePgData = Join-Path $intakeData 'postgres-intake'
if (-not (Test-Path -LiteralPath (Join-Path $intakePgData 'PG_VERSION'))) {
    Intake-Status 'Initializing only the new isolated demo PostgreSQL cluster'
    & (Join-Path $intakePgBin 'initdb.exe') -D $intakePgData -U wallet -A trust --encoding=UTF8 --locale=C
    if ($LASTEXITCODE -ne 0) { throw 'Isolated PostgreSQL initialization failed' }
}
$intakePgConfig = @{bin=$intakePgBin; data=$intakePgData; root=$intakeRoot}
$intakePgConfig | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $intakeData 'intake-postgres.json') -Encoding utf8
# Direct native redirection can leave PowerShell waiting on a daemon's inherited
# handles. Wait on pg_ctl itself, with output redirected to files at process creation.
$intakePgStart=Start-Process -FilePath (Join-Path $intakePgBin 'pg_ctl.exe') -ArgumentList @('-D', ('"'+$intakePgData+'"'), '-l', ('"'+(Join-Path $intakeData 'intake-postgres.log')+'"'), '-o', ('"-p '+$PgPort+' -h 127.0.0.1"'), '-w', 'start') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $intakeData 'intake-pgctl.stdout.log') -RedirectStandardError (Join-Path $intakeData 'intake-pgctl.stderr.log')
$null=$intakePgStart.Handle
$intakePgStarted=$intakePgStart.WaitForExit(45000)
$intakePgStart.Refresh()
if (-not $intakePgStarted -or $intakePgStart.ExitCode -ne 0) { throw 'Isolated PostgreSQL start failed; inspect this worktree logs' }
$env:PGHOST='127.0.0.1'; $env:PGPORT=[string]$PgPort; $env:PGUSER='wallet'; $env:PGDATABASE='postgres'
& $intakePython -c "import psycopg; c=psycopg.connect(autocommit=True); exists=c.execute('SELECT 1 FROM pg_database WHERE datname=%s',('wallet_intake_demo',)).fetchone(); c.execute('CREATE DATABASE wallet_intake_demo') if not exists else None; c.close()"
if ($LASTEXITCODE -ne 0) { throw 'Isolated database creation failed' }
$env:NODE_PATH=(Join-Path $intakeRoot 'spring-boot-service\node_modules') + ';' + (Join-Path $intakeRoot 'node_modules') + ';' + (Join-Path $RuntimeRoot 'spring-boot-service\node_modules') + ';' + (Join-Path $RuntimeRoot 'node_modules')
$env:FOLIOLET_EVM_PORT=[string]$EvmPort
Intake-Launch 'intake-evm' (Get-Command node).Source @((Join-Path $intakeRoot 'tools\digilocker-evm.cjs')) $intakeRoot
Intake-Wait $EvmPort
$env:BLOCKCHAIN_PRIVATE_KEY=(Get-Content -LiteralPath (Join-Path $intakeData 'development-relay.key') -Raw).Trim()
$env:SPRING_DATASOURCE_URL="jdbc:postgresql://127.0.0.1:$PgPort/wallet_intake_demo"
$env:SPRING_DATASOURCE_USERNAME='wallet'; $env:SPRING_DATASOURCE_PASSWORD=''
$env:SPRING_JPA_HIBERNATE_DDL_AUTO='update'; $env:SPRING_JPA_OPEN_IN_VIEW='false'
$env:BLOCKCHAIN_RPC_URL="http://127.0.0.1:$EvmPort"; $env:BLOCKCHAIN_EXPECTED_CHAIN_ID='1337'
$env:WALLET_DATA_DIR=$intakeData; $env:WALLET_SHARE_BASE_URL="http://localhost:$UiPort"
$env:DMS_STORAGE_LOCATION=(Join-Path $intakeData 'legacy\files'); $env:DMS_BACKUP_LOCATION=(Join-Path $intakeData 'legacy\backups')
$env:SERVER_ADDRESS='127.0.0.1'; $env:SERVER_PORT=[string]$ApiPort
$env:SPRING_SERVLET_MULTIPART_MAX_FILE_SIZE='20MB'; $env:SPRING_SERVLET_MULTIPART_MAX_REQUEST_SIZE='21MB'
$env:OPENROUTER_API_KEY=''; $env:OPENROUTER_MODEL='disabled-for-intake'; $env:FOLI_MODEL='qwen3:4b-instruct'; $env:FOLI_OLLAMA_URL=$OllamaUrl
$env:FOLI_TESSERACT=$intakeOcr; $env:FOLI_OCR_DATA_DIR=(Join-Path $RuntimeRoot '.local-tools\ocr\share\tessdata')
$env:FOLI_LAYOUT_PYTHON=$intakePython; $env:FOLI_LAYOUT_SCRIPT=(Join-Path $intakeRoot 'tools\ocr-layout-worker.py')
$env:FOLI_TEMP_DIR=(Join-Path $intakeData 'foli\tmp')
$env:LOGGING_LEVEL_ORG_APACHE_PDFBOX='OFF'; $env:LOGGING_LEVEL_ORG_SPRINGFRAMEWORK_AI='OFF'
$env:SERVER_TOMCAT_ACCESSLOG_ENABLED='false'
Intake-Launch 'intake-spring' (Get-Command java).Source @("-Xmx${MaxHeapMb}m", '-jar', (Join-Path $intakeRoot 'spring-boot-service\target\dms-0.0.1-SNAPSHOT.jar')) (Join-Path $intakeRoot 'spring-boot-service')
Intake-Wait $ApiPort 90
& node (Join-Path $intakeRoot 'tools\provision-digilocker-trust.cjs')
if ($LASTEXITCODE -ne 0) { throw 'Isolated registry trust provisioning failed' }
$env:SPRING_BOOT_API_BASE_URL="http://127.0.0.1:$ApiPort"; $env:PUBLIC_EVM_RPC_URL="http://127.0.0.1:$EvmPort"
# Keep the private UI local; publish selected disclosure links through the receiver.
$env:FOLIOLET_SHARE_MODE='quick'
$env:FOLIOLET_RECEIVER_PORT=[string]$folioletPorts.receiver
$env:FOLIOLET_CONTROL_PORT=[string]$folioletPorts.control
if (-not $env:CLOUDFLARED_PATH) {
    $intakeCloudflared=Join-Path $RuntimeRoot '.local-tools\cloudflared\cloudflared.exe'
    if (Test-Path -LiteralPath $intakeCloudflared) { $env:CLOUDFLARED_PATH=$intakeCloudflared }
}
$env:DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1,testserver'
& $intakePython (Join-Path $intakeRoot 'django-service\manage.py') migrate --noinput
if ($LASTEXITCODE -ne 0) { throw 'Private Django migration failed' }
Intake-Launch 'intake-django' $intakePython @((Join-Path $intakeRoot 'django-service\manage.py'), 'runserver', "127.0.0.1:$UiPort", '--noreload') $intakeRoot
Intake-Wait $UiPort
Intake-Status 'Starting Cloudflare receiver sharing'
& $intakePython (Join-Path $intakeRoot 'tools\share-tunnel.py') start
if ($LASTEXITCODE -ne 0) { throw 'Cloudflare receiver sharing could not start; inspect the tunnel startup message.' }
& (Join-Path $PSScriptRoot 'start-digilocker-watcher.ps1') -Resume
Intake-Status ("Ready: http://127.0.0.1:$UiPort/; sharing mode: " + $env:FOLIOLET_SHARE_MODE)
if (-not (Test-Path -LiteralPath $intakeOcr)) { Intake-Status 'OCR is unavailable; originals and manual facts still work.' }
try {
    $intakeModel=Invoke-RestMethod ($OllamaUrl.TrimEnd('/')+'/api/tags') -TimeoutSec 3
    $intakeSelected=$intakeModel.models | Where-Object {$_.name -eq 'qwen3:4b-instruct'}
    if (-not $intakeSelected) { Intake-Status 'Local model missing. No model was downloaded; manual fallback remains available.' }
} catch { Intake-Status 'Ollama offline. No model was started or downloaded; manual fallback remains available.' }
