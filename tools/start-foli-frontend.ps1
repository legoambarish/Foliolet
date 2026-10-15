$ErrorActionPreference = 'Stop'
$foliRoot = Split-Path -Parent $PSScriptRoot
if ((git -C $foliRoot branch --show-current).Trim() -ne 'cf') { throw 'Foli requires the existing cf branch.' }
$env:FOLIOLET_SHARE_MODE = 'local'
& (Join-Path $PSScriptRoot 'start-frontend.ps1')
