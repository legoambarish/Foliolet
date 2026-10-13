param([switch]$Launch)
$ErrorActionPreference='Stop'
$bridgeRoot=Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'stop-bridge-demo.ps1')
foreach($bridgePort in 8000,8080,8090,8545,8001){if(Get-NetTCPConnection -LocalPort $bridgePort -State Listen -ErrorAction SilentlyContinue){throw "Port $bridgePort is owned by a process outside the launcher. Stop that owned demo process before reset."}}
$bridgeData=[IO.Path]::GetFullPath((Join-Path $bridgeRoot '.bridge-data'))
$bridgeArchive=Join-Path $bridgeData ('archive\'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $bridgeArchive -Force | Out-Null
# Exact allowlist; archive rather than delete. Models, tools, logs and verification captures survive.
foreach($bridgeName in @('postgres','chain','config','backend','frontend','public-frontend')){
 $bridgeTarget=[IO.Path]::GetFullPath((Join-Path $bridgeData $bridgeName))
 if(-not $bridgeTarget.StartsWith($bridgeData+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Reset target escaped demo directory'}
 if(Test-Path -LiteralPath $bridgeTarget){if((Get-Item -LiteralPath $bridgeTarget).Attributes-band [IO.FileAttributes]::ReparsePoint){throw 'Refusing ambiguous reparse reset target'};Move-Item -LiteralPath $bridgeTarget -Destination (Join-Path $bridgeArchive $bridgeName)}
}
Write-Output "Demo state archived under $bridgeArchive; legacy data and main untouched."
if($Launch){& (Join-Path $PSScriptRoot 'start-bridge-demo.ps1')}
