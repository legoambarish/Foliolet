param([Parameter(Mandatory=$true)][string]$RuntimeRoot)
$ErrorActionPreference='Stop'
$intakeRoot=(Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
$RuntimeRoot=(Resolve-Path -LiteralPath $RuntimeRoot).Path
if ((git -C $intakeRoot branch --show-current).Trim() -notlike 'feature/digilocker-assisted-intake*') { throw 'Use the dedicated intake feature worktree.' }
if (Get-NetTCPConnection -State Listen -LocalPort 11444 -ErrorAction SilentlyContinue) { throw 'Port 11444 is occupied. No process was changed.' }
function Copy-IntakeRuntimeFile([string]$Source,[string]$Destination,[string]$ExpectedHash) {
    if (-not $ExpectedHash) { $ExpectedHash=(Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash }
    if (-not (Test-Path -LiteralPath $Destination)) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
        $intakePartial=$Destination+'.'+[guid]::NewGuid().ToString('N')+'.partial'
        Copy-Item -LiteralPath $Source -Destination $intakePartial
        if ((Get-FileHash -LiteralPath $intakePartial -Algorithm SHA256).Hash -ne $ExpectedHash) { throw 'Runtime copy hash mismatch; partial retained.' }
        Move-Item -LiteralPath $intakePartial -Destination $Destination
    }
    if ((Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash -ne $ExpectedHash) { throw 'Existing private runtime file differs; no overwrite performed.' }
}
$intakeOllama=Join-Path $intakeRoot '.local-tools\intake-ollama'
$intakeSource=Join-Path $RuntimeRoot '.local-tools\ollama'
Write-Host ('['+(Get-Date -Format HH:mm:ss)+'] Copying only the retained CPU runtime and selected model; no download.')
Copy-IntakeRuntimeFile (Join-Path $intakeSource 'ollama.exe') (Join-Path $intakeOllama 'ollama.exe') ''
# Top-level CPU DLLs/licenses only. GPU backend subdirectories are not copied.
foreach ($intakeFile in Get-ChildItem -LiteralPath (Join-Path $intakeSource 'lib\ollama') -File) {
    Copy-IntakeRuntimeFile $intakeFile.FullName (Join-Path $intakeOllama ('lib\ollama\'+$intakeFile.Name)) ''
}
$intakeModelSource=Join-Path $RuntimeRoot '.local-data\foli\models'
$intakeModels=Join-Path $intakeRoot '.local-data\intake-models'
$intakeManifestRelative='manifests\registry.ollama.ai\library\qwen3\4b-instruct'
$intakeManifestSource=Join-Path $intakeModelSource $intakeManifestRelative
$intakeModel=Get-Content -LiteralPath $intakeManifestSource -Raw | ConvertFrom-Json
$intakeEntries=@($intakeModel.config)+@($intakeModel.layers)
if (($intakeEntries | Measure-Object -Property size -Sum).Sum -ge 5000000000) { throw 'Selected package exceeds the local 5 GB budget.' }
foreach ($intakeBlob in $intakeEntries) {
    if ($intakeBlob.digest -notmatch '^sha256:[0-9a-f]{64}$') { throw 'Invalid retained model digest' }
    $intakeBlobName=$intakeBlob.digest.Replace(':','-')
    Write-Host ('['+(Get-Date -Format HH:mm:ss)+'] Checking retained model layer ('+$intakeBlob.size+' bytes).')
    Copy-IntakeRuntimeFile (Join-Path $intakeModelSource ('blobs\'+$intakeBlobName)) (Join-Path $intakeModels ('blobs\'+$intakeBlobName)) $intakeBlob.digest.Substring(7)
}
Copy-IntakeRuntimeFile $intakeManifestSource (Join-Path $intakeModels $intakeManifestRelative) ''
$env:OLLAMA_HOST='127.0.0.1:11444';$env:OLLAMA_MODELS=$intakeModels;$env:OLLAMA_NO_CLOUD='1';$env:OLLAMA_NOPRUNE='1'
$env:OLLAMA_NUM_PARALLEL='1';$env:OLLAMA_MAX_LOADED_MODELS='1';$env:CUDA_VISIBLE_DEVICES='-1';$env:ROCR_VISIBLE_DEVICES='-1';$env:GGML_VK_VISIBLE_DEVICES='-1';$env:OLLAMA_VULKAN='0'
$intakeData=Join-Path $intakeRoot '.local-data'
$intakeProcess=Start-Process -FilePath (Join-Path $intakeOllama 'ollama.exe') -ArgumentList 'serve' -WorkingDirectory $intakeRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $intakeData 'intake-model.stdout.log') -RedirectStandardError (Join-Path $intakeData 'intake-model.stderr.log')
@{name='intake-model';pid=$intakeProcess.Id;started=$intakeProcess.StartTime.ToUniversalTime().ToString('o');root=$intakeRoot} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $intakeData 'intake-model-process.json') -Encoding utf8
$intakeDeadline=(Get-Date).AddSeconds(30)
while ((Get-Date) -lt $intakeDeadline) {
    try {
        $intakeHealth=Invoke-RestMethod 'http://127.0.0.1:11444/api/status' -TimeoutSec 2
        if ($intakeHealth.cloud.disabled) { Write-Host 'Owned CPU model service ready at 127.0.0.1:11444. No existing Ollama service or model was changed.'; exit 0 }
    } catch { }
    Start-Sleep -Seconds 2
}
throw 'Owned model service failed readiness; inspect .local-data/intake-model.stderr.log.'
