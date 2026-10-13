$ErrorActionPreference='Stop'
$bridgeRoot=Split-Path -Parent $PSScriptRoot
$bridgeData=Join-Path $bridgeRoot '.bridge-data\postgres'
$bridgeBin=Join-Path $bridgeRoot '.local-tools\postgres\bin'
New-Item -ItemType Directory -Path $bridgeData -Force | Out-Null
if(-not(Test-Path -LiteralPath (Join-Path $bridgeData 'PG_VERSION'))){& (Join-Path $bridgeBin 'initdb.exe') -D $bridgeData -U foliolet -A trust --encoding=UTF8 --locale=C;if($LASTEXITCODE -ne 0){throw 'Demo initdb failed'}}
& (Join-Path $bridgeBin 'pg_ctl.exe') -D $bridgeData status | Out-Null
if($LASTEXITCODE -ne 0){& (Join-Path $bridgeBin 'pg_ctl.exe') -D $bridgeData -l (Join-Path $bridgeRoot '.bridge-data\postgres.log') -o '-p 55433 -h 127.0.0.1' -w start;if($LASTEXITCODE -ne 0){throw 'Demo postgres failed'}}
& (Join-Path $bridgeRoot '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'create-bridge-database.py')
if($LASTEXITCODE -ne 0){throw 'Demo database creation failed'}
Write-Output 'Isolated demo PostgreSQL ready at 127.0.0.1:55433; local trust authentication only.'
