$ErrorActionPreference='Stop'
$bridgeRoot=Split-Path -Parent $PSScriptRoot
$env:OLLAMA_HOST='127.0.0.1:11434'
$env:OLLAMA_MODELS=Join-Path $bridgeRoot '.bridge-data\models'
$env:OLLAMA_NUM_PARALLEL='1';$env:OLLAMA_MAX_LOADED_MODELS='1';$env:OLLAMA_KEEP_ALIVE='10m'
$env:OLLAMA_NO_CLOUD='true'
& (Join-Path $bridgeRoot '.bridge-data\tools\ollama\ollama.exe') serve
