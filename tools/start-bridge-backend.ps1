param([switch]$UseJar)
$ErrorActionPreference='Stop'
$bridgeRoot=Split-Path -Parent $PSScriptRoot
Get-Content (Join-Path $bridgeRoot '.bridge-data\config\demo.env') | ForEach-Object {if($_ -match '^([A-Z_]+)=(.*)$'){[Environment]::SetEnvironmentVariable($Matches[1],$Matches[2],'Process')}}
$env:BRIDGE_ENABLED='true';$env:BRIDGE_DEMO='true'
$env:SPRING_DATASOURCE_URL='jdbc:postgresql://127.0.0.1:55433/foliolet_bridge';$env:SPRING_DATASOURCE_USERNAME='foliolet';$env:SPRING_DATASOURCE_PASSWORD=''
$env:WALLET_DATA_DIR=Join-Path $bridgeRoot '.bridge-data\backend'
$env:DMS_STORAGE_LOCATION=Join-Path $env:WALLET_DATA_DIR 'legacy\files';$env:DMS_BACKUP_LOCATION=Join-Path $env:WALLET_DATA_DIR 'legacy\backups'
# Use packaged config only. Retained local application.properties belongs to the legacy workspace.
$env:SPRING_CONFIG_LOCATION='classpath:/application.yaml'
Set-Location (Join-Path $bridgeRoot 'spring-boot-service')
if($UseJar){& java -jar target/dms-0.0.1-SNAPSHOT.jar}else{& .\mvnw.cmd -B spring-boot:run}
