$ErrorActionPreference='Stop'
$bridgeRoot=Split-Path -Parent $PSScriptRoot
$env:DJANGO_PRIVATE_DIR=Join-Path $bridgeRoot '.bridge-data\public-frontend'
$env:BRIDGE_PINS_FILE=Join-Path $bridgeRoot '.bridge-data\config\bridge-pins.json'
$env:PUBLIC_LOCAL_HTTP='true'
$env:DJANGO_SETTINGS_MODULE='hermes.public_settings'
New-Item -ItemType Directory -Path $env:DJANGO_PRIVATE_DIR -Force | Out-Null
Set-Location (Join-Path $bridgeRoot 'django-service')
& ..\.venv\Scripts\python.exe manage.py migrate --noinput
& ..\.venv\Scripts\python.exe manage.py collectstatic --noinput
& ..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001 --noreload
