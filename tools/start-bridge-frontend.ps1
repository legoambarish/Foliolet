$ErrorActionPreference='Stop'
$bridgeRoot=Split-Path -Parent $PSScriptRoot
$env:DJANGO_PRIVATE_DIR=Join-Path $bridgeRoot '.bridge-data\frontend'
$env:BRIDGE_PINS_FILE=Join-Path $bridgeRoot '.bridge-data\config\bridge-pins.json'
$env:WALLET_TRUST_FILE=Join-Path $bridgeRoot '.bridge-data\config\trusted-deployment.json'
New-Item -ItemType Directory -Path $env:DJANGO_PRIVATE_DIR -Force | Out-Null
Set-Location (Join-Path $bridgeRoot 'django-service')
& ..\.venv\Scripts\python.exe manage.py migrate --noinput
& ..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
