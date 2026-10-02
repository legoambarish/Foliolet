# Optional portable PostgreSQL for this Windows localhost demo. Does not alter a system installation.
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskTools = Join-Path $taskRoot '.local-tools'
$taskBin = Join-Path $taskTools 'postgres\bin\pg_ctl.exe'
if (Test-Path -LiteralPath $taskBin) { Write-Output 'Portable PostgreSQL already present.'; exit 0 }
New-Item -ItemType Directory -Path $taskTools -Force | Out-Null
$taskJar = Join-Path $taskTools 'postgres.jar'
$taskUri = 'https://repo.maven.apache.org/maven2/io/zonky/test/postgres/embedded-postgres-binaries-windows-amd64/17.6.0/embedded-postgres-binaries-windows-amd64-17.6.0.jar'
Write-Output 'Downloading pinned PostgreSQL 17.6 development binaries from Maven Central...'
Invoke-WebRequest -Uri $taskUri -OutFile $taskJar
$taskHash = (Get-FileHash -LiteralPath $taskJar -Algorithm SHA256).Hash
if ($taskHash -ne 'C91D39B6DB91CF8811E3B20D941E74A0396E277360873821DAAB47CDB4C1282C') { throw 'PostgreSQL archive checksum mismatch' }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$taskZip = [System.IO.Compression.ZipFile]::OpenRead($taskJar)
$taskTxz = Join-Path $taskTools 'postgres-windows-x86_64.txz'
try { [System.IO.Compression.ZipFileExtensions]::ExtractToFile($taskZip.GetEntry('postgres-windows-x86_64.txz'), $taskTxz, $true) }
finally { $taskZip.Dispose() }
$taskDestination = Join-Path $taskTools 'postgres'
New-Item -ItemType Directory -Path $taskDestination -Force | Out-Null
& tar.exe -xJf $taskTxz -C $taskDestination
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $taskBin)) { throw 'PostgreSQL extraction failed' }
Write-Output 'Portable PostgreSQL installed in .local-tools/postgres. Start with tools/start-postgres.ps1.'
