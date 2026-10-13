param([switch]$SkipBuild,[switch]$WithAI,[switch]$WithPublicPreview)
$ErrorActionPreference='Stop'
$bridgeRoot=Split-Path -Parent $PSScriptRoot
Set-Location $bridgeRoot
$bridgeLogs=Join-Path $bridgeRoot '.bridge-data\logs'
New-Item -ItemType Directory -Path $bridgeLogs -Force | Out-Null
$bridgeManaged=Join-Path $bridgeRoot '.bridge-data\processes.json'
$bridgeProcesses=@()
if(Test-Path -LiteralPath $bridgeManaged){$bridgeProcesses=@(Get-Content -Raw -LiteralPath $bridgeManaged | ConvertFrom-Json)}
function Save-BridgeProcesses {ConvertTo-Json -InputObject @($script:bridgeProcesses) -Depth 4 | Set-Content -LiteralPath $script:bridgeManaged}
function Start-BridgeProcess($Name,$Arguments){
 $bridgeChild=Start-Process -FilePath powershell.exe -ArgumentList (@('-NoProfile','-ExecutionPolicy','Bypass')+$Arguments) -WorkingDirectory $script:bridgeRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $script:bridgeLogs "$Name.log") -RedirectStandardError (Join-Path $script:bridgeLogs "$Name.err.log")
 $script:bridgeProcesses+=@{name=$Name;pid=$bridgeChild.Id;started=$bridgeChild.StartTime.ToUniversalTime().ToString('o');workspace=$script:bridgeRoot};Save-BridgeProcesses
 Write-Output "$(Get-Date -Format o) / $Name started (PID $($bridgeChild.Id))"
}
function Wait-BridgeHttp($Name,$Url){
 $bridgeDeadline=(Get-Date).AddSeconds(150);$bridgeNextNotice=Get-Date
 while((Get-Date)-lt $bridgeDeadline){try{$bridgeResponse=Invoke-WebRequest $Url -TimeoutSec 3 -UseBasicParsing;if($bridgeResponse.StatusCode-eq 200){Write-Output "$(Get-Date -Format o) / $Name ready";return}}catch{};if((Get-Date)-ge $bridgeNextNotice){Write-Output "$(Get-Date -Format o) / waiting for $Name; see .bridge-data/logs";$bridgeNextNotice=(Get-Date).AddSeconds(15)};Start-Sleep -Seconds 1}
 throw "$Name did not become ready; inspect .bridge-data/logs"
}
if(-not(Test-Path .venv/Scripts/python.exe)){& python -m venv .venv;& ./.venv/Scripts/python.exe -m pip install -r django-service/requirements.txt;if($LASTEXITCODE-ne 0){throw 'Python setup failed'}}
if(-not(Test-Path .local-tools/postgres/bin/pg_ctl.exe)){& ./tools/setup-local-postgres.ps1}
if(-not(Test-Path spring-boot-service/node_modules/ethers)){& npm ci --prefix spring-boot-service;if($LASTEXITCODE-ne 0){throw 'Node setup failed'}}
if(-not $SkipBuild){Write-Output "$(Get-Date -Format o) / building Spring";& ./spring-boot-service/mvnw.cmd -f spring-boot-service/pom.xml -B package -DskipTests;if($LASTEXITCODE-ne 0){throw 'Spring build failed'}}
& ./tools/start-bridge-postgres.ps1
if(-not(Get-NetTCPConnection -LocalPort 8545 -State Listen -ErrorAction SilentlyContinue)){Start-BridgeProcess 'chain' @('-Command','node spring-boot-service/scripts/bridge-chain.cjs')}
$bridgeChainReady=$false
for($bridgeAttempt=0;$bridgeAttempt-lt 30;$bridgeAttempt++){try{$bridgeRpc=Invoke-RestMethod 'http://127.0.0.1:8545' -Method Post -ContentType 'application/json' -Body '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' -TimeoutSec 2;if($bridgeRpc.result-eq '0x539'){$bridgeChainReady=$true;break}}catch{};Start-Sleep -Seconds 1}
if(-not $bridgeChainReady){throw 'Expected local chain 1337 unavailable'}
Write-Output "$(Get-Date -Format o) / checking chain and seeding governed test actors"
& node spring-boot-service/scripts/bridge-seed.cjs
if($LASTEXITCODE-ne 0){throw 'Chain seed failed; no application started'}
if(-not(Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue)){Start-BridgeProcess 'backend' @('-File',('"'+(Join-Path $bridgeRoot 'tools/start-bridge-backend.ps1')+'"'),'-UseJar')}
Wait-BridgeHttp 'Spring' 'http://127.0.0.1:8080/api/public/health'
if(-not(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)){Start-BridgeProcess 'frontend' @('-File',('"'+(Join-Path $bridgeRoot 'tools/start-bridge-frontend.ps1')+'"'))}
if(-not(Get-NetTCPConnection -LocalPort 8090 -State Listen -ErrorAction SilentlyContinue)){Start-BridgeProcess 'reader' @('-Command','.\.venv\Scripts\python.exe tools/serve-reader.py')}
Wait-BridgeHttp 'Django' 'http://127.0.0.1:8000/health/'
Wait-BridgeHttp 'Independent reader' 'http://127.0.0.1:8090/'
if($WithAI){if(-not(Test-Path .bridge-data/tools/ollama/ollama.exe)){& ./.venv/Scripts/python.exe tools/setup-local-ai.py};if(-not(Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue)){Start-BridgeProcess 'ollama' @('-File',('"'+(Join-Path $bridgeRoot 'tools/start-local-ai.ps1')+'"'))};Wait-BridgeHttp 'Ollama' 'http://127.0.0.1:11434/api/tags'}
if($WithPublicPreview){if(-not(Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue)){Start-BridgeProcess 'public' @('-File',('"'+(Join-Path $bridgeRoot 'tools/start-public-demo.ps1')+'"'))};Wait-BridgeHttp 'Restricted local public preview' 'http://127.0.0.1:8001/health/'}
Write-Output 'Foliolet ready: http://127.0.0.1:8000/bridge/ ; reader http://127.0.0.1:8090/ . No external tunnel was started.'
