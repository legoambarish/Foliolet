$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $taskRoot 'django-service')
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
& $taskPython manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { throw 'Django migrations failed' }
& $taskPython manage.py runserver 127.0.0.1:8000 --noreload
