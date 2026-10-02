param([string]$PostgresBin)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
if (-not $PostgresBin) { $PostgresBin = Join-Path $taskRoot '.local-tools\postgres\bin' }
$taskPgData = Join-Path $taskRoot '.local-data\postgres'
if (-not (Test-Path -LiteralPath (Join-Path $taskPgData 'PG_VERSION'))) {
    New-Item -ItemType Directory -Path $taskPgData -Force | Out-Null
    & (Join-Path $PostgresBin 'initdb.exe') -D $taskPgData -U wallet -A trust --encoding=UTF8 --locale=C
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL initialization failed' }
}
& (Join-Path $PostgresBin 'pg_ctl.exe') -D $taskPgData status | Out-Null
if ($LASTEXITCODE -ne 0) { & (Join-Path $PostgresBin 'pg_ctl.exe') -D $taskPgData -l (Join-Path $taskRoot '.local-data\postgres.log') -o '-p 55432 -h 127.0.0.1' -w start }
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
& $taskPython (Join-Path $PSScriptRoot 'create-dev-database.py')
if ($LASTEXITCODE -ne 0) { throw 'Database creation failed' }
Write-Output 'Local PostgreSQL ready at 127.0.0.1:55432. Trust authentication is for local development only.'
