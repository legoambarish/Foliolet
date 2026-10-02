$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $taskRoot 'spring-boot-service')
# The EVM launcher creates this ignored local key; never publish it with the source.
if (-not $env:BLOCKCHAIN_PRIVATE_KEY) {
    $taskRelayPath = Join-Path $taskRoot '.local-data\development-relay.key'
    if (-not (Test-Path -LiteralPath $taskRelayPath)) { throw 'Start npm run evm first, or supply BLOCKCHAIN_PRIVATE_KEY.' }
    $env:BLOCKCHAIN_PRIVATE_KEY = (Get-Content -LiteralPath $taskRelayPath -Raw).Trim()
}
& .\mvnw.cmd spring-boot:run
