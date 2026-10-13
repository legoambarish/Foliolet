param([string[]]$Names=@('backend','frontend','reader','chain','ollama','public'),[switch]$KeepDatabase)
$ErrorActionPreference='Stop'
$bridgeRoot=Split-Path -Parent $PSScriptRoot
$bridgeManaged=Join-Path $bridgeRoot '.bridge-data\processes.json'
if(Test-Path -LiteralPath $bridgeManaged){
 $bridgeRecords=@(Get-Content -Raw -LiteralPath $bridgeManaged | ConvertFrom-Json)
 foreach($bridgeRecord in $bridgeRecords){
  if($bridgeRecord.name-notin $Names){continue}
  $bridgeProcess=Get-Process -Id $bridgeRecord.pid -ErrorAction SilentlyContinue
  if(-not $bridgeProcess){continue}
  $bridgeStarted=if($bridgeRecord.started-is [DateTime]){$bridgeRecord.started}else{[DateTime]::Parse($bridgeRecord.started,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind)}
  if($bridgeRecord.workspace-ne $bridgeRoot -or [Math]::Abs(($bridgeProcess.StartTime.ToUniversalTime()-$bridgeStarted.ToUniversalTime()).TotalSeconds)-gt 2){throw 'Managed PID no longer matches the recorded demo process'}
  $bridgeAll=Get-CimInstance Win32_Process
  $bridgeOwned=@([int]$bridgeRecord.pid)
  for($bridgeDepth=0;$bridgeDepth-lt 8;$bridgeDepth++){$bridgeChildren=@($bridgeAll | Where-Object {$_.ParentProcessId-in $bridgeOwned -and $_.ProcessId-notin $bridgeOwned} | Select-Object -ExpandProperty ProcessId);if(-not $bridgeChildren.Count){break};$bridgeOwned+=$bridgeChildren}
  foreach($bridgeId in ($bridgeOwned | Sort-Object -Descending)){Stop-Process -Id $bridgeId -ErrorAction SilentlyContinue}
  Write-Output "Stopped owned demo $($bridgeRecord.name)"
 }
 ConvertTo-Json -InputObject @($bridgeRecords | Where-Object {$_.name-notin $Names}) -Depth 4 | Set-Content -LiteralPath $bridgeManaged
}
$bridgeDb=Join-Path $bridgeRoot '.bridge-data\postgres'
if(-not $KeepDatabase -and (Test-Path -LiteralPath (Join-Path $bridgeDb 'PG_VERSION'))){& (Join-Path $bridgeRoot '.local-tools\postgres\bin\pg_ctl.exe') -D $bridgeDb -m fast -w stop}
