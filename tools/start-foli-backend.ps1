param([string]$Model = 'qwen3:4b-instruct')
$ErrorActionPreference = 'Stop'
$foliRoot = Split-Path -Parent $PSScriptRoot
if ((git -C $foliRoot branch --show-current).Trim() -ne 'cf') { throw 'Foli requires the existing cf branch.' }
$env:FOLI_MODEL = $Model
$env:SERVER_ADDRESS = '127.0.0.1'
$env:FOLI_OLLAMA_URL = 'http://127.0.0.1:11434'
$env:FOLI_TESSERACT = Join-Path $foliRoot '.local-tools\ocr\Library\bin\tesseract.exe'
$env:FOLI_OCR_DATA_DIR = Join-Path $foliRoot '.local-tools\ocr\share\tessdata'
$env:FOLI_TEMP_DIR = Join-Path $foliRoot '.local-data\foli\tmp'
$env:LOGGING_LEVEL_ORG_APACHE_PDFBOX = 'OFF'
$env:LOGGING_LEVEL_ORG_SPRINGFRAMEWORK_AI = 'OFF'
$env:SERVER_TOMCAT_ACCESSLOG_ENABLED = 'false'
if (-not (Test-Path -LiteralPath $env:FOLI_TESSERACT)) { throw 'Run tools/setup-foli-runtime.py first.' }
& (Join-Path $PSScriptRoot 'start-backend.ps1')
