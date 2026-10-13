param([switch]$ProveOffline)
$ErrorActionPreference='Stop'
$bridgeRoot=Split-Path -Parent $PSScriptRoot
Set-Location $bridgeRoot
New-Item -ItemType Directory -Path .bridge-data/artifacts -Force | Out-Null
Write-Output "$(Get-Date -Format o) / rehearsal start: test identities and live local EVM"
& ./tools/stop-bridge-demo.ps1 -Names @('ollama') -KeepDatabase
if(Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue){throw 'AI is still running outside the managed launcher. Stop your owned local AI process before this no-AI rehearsal.'}
& node spring-boot-service/scripts/test-bridge-live.cjs
if($LASTEXITCODE-ne 0){throw 'Primary live rehearsal failed'}
& node spring-boot-service/scripts/test-bridge-workflows.cjs
if($LASTEXITCODE-ne 0){throw 'Approval/import/secondary scenario rehearsal failed'}
if($ProveOffline){
 & ./tools/stop-bridge-demo.ps1 -Names @('backend','frontend') -KeepDatabase
 foreach($bridgePort in 8000,8080,11434){if(Get-NetTCPConnection -LocalPort $bridgePort -State Listen -ErrorAction SilentlyContinue){throw "Expected app/AI port $bridgePort to be closed"}}
 & node spring-boot-service/scripts/bridge-reader.cjs .bridge-data/artifacts/bundle.json .bridge-data/config/bridge-pins.json --historical .bridge-data/artifacts/decision.json | Tee-Object -FilePath .bridge-data/artifacts/offline-historical.log
 if($LASTEXITCODE-ne 0){throw 'Independent historical reproduction failed'}
 & node spring-boot-service/scripts/bridge-reader.cjs .bridge-data/artifacts/income-bundle.json .bridge-data/config/bridge-pins.json | Tee-Object -FilePath .bridge-data/artifacts/offline-current.log
 if($LASTEXITCODE-ne 0){throw 'Independent current reliance failed'}
 $bridgeProof=@{appPortsClosed=@(8000,8080,11434);chainReachable=$true;readerReachable=(Invoke-WebRequest 'http://127.0.0.1:8090/' -UseBasicParsing).StatusCode-eq 200;historical='PASS';current='PASS';at=(Get-Date -Format o)}
 & ./tools/stop-bridge-demo.ps1 -Names @('chain') -KeepDatabase
 & node spring-boot-service/scripts/bridge-reader.cjs .bridge-data/artifacts/income-bundle.json .bridge-data/config/bridge-pins.json | Tee-Object -FilePath .bridge-data/artifacts/offline-no-chain.log
 if($LASTEXITCODE-ne 2){throw 'Unavailable current chain must yield UNKNOWN (exit 2)'}
 $bridgeProof.chainUnavailable='UNKNOWN';$bridgeProof | ConvertTo-Json | Set-Content .bridge-data/artifacts/offline-results.json
 & ./tools/start-bridge-demo.ps1 -SkipBuild -WithAI
}
Write-Output "$(Get-Date -Format o) / rehearsal passed; see ignored .bridge-data/artifacts and docs/DEMO_RUNBOOK.md"
