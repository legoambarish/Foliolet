$ErrorActionPreference = 'Stop'
$foliRoot = Split-Path -Parent $PSScriptRoot
if ((git -C $foliRoot branch --show-current).Trim() -ne 'cf') { throw 'Foli requires cf.' }
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_MODELS = Join-Path $foliRoot '.local-data\foli\models'
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:OLLAMA_MAX_QUEUE = '4'
$env:OLLAMA_KEEP_ALIVE = '10m'
$env:OLLAMA_CONTEXT_LENGTH = '8192'
$env:OLLAMA_DEBUG = '0'
& (Join-Path $foliRoot '.local-tools\ollama\ollama.exe') serve
