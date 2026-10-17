param([switch]$NoBrowser, [switch]$SmokeTest, [string]$CapturePath)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'foliolet-desktop-common.ps1')
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()
$uiMutex = New-Object Threading.Mutex($false, ('Local\FolioletWindow-' + $folioletIdentity))
$uiLocked=$false
try { $uiLocked=$uiMutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $uiLocked=$true }
if (-not $uiLocked) {
    try { Assert-FolioletOwnedPorts; if (-not $NoBrowser -and (Test-FolioletReady)) { Start-Process $folioletUrl } } catch { }
    $shell=New-Object -ComObject WScript.Shell
    $null=$shell.AppActivate('Foliolet')
    $uiMutex.Dispose()
    exit 0
}
New-Item -ItemType Directory -Path $folioletData -Force | Out-Null
$script:uiStatus=Join-Path $folioletData 'desktop-status.json'
$script:worker=$null
$script:browserOpened=$false
$script:uiExit=0
$script:finished=$false
$script:finishedAt=$null
$script:exitSeenAt=$null
$script:startedAt=Get-Date
$script:captured=$false
$form=New-Object Windows.Forms.Form
$form.Text='Foliolet'
$form.ClientSize=New-Object Drawing.Size(544,330)
$form.MinimumSize=New-Object Drawing.Size(560,369)
$form.MaximumSize=$form.MinimumSize
$form.StartPosition='CenterScreen'
$form.BackColor=[Drawing.ColorTranslator]::FromHtml('#F6F4F9')
$form.Font=New-Object Drawing.Font('Segoe UI',10)
$form.Icon=[Drawing.SystemIcons]::Application
$title=New-Object Windows.Forms.Label
$title.Text='Foliolet'
$title.Font=New-Object Drawing.Font('Segoe UI Semibold',28)
$title.ForeColor=[Drawing.ColorTranslator]::FromHtml('#573D85')
$title.SetBounds(24,19,490,60)
$form.Controls.Add($title)
$subtitle=New-Object Windows.Forms.Label
$subtitle.Text='Your private document workspace'
$subtitle.SetBounds(27,83,485,26)
$form.Controls.Add($subtitle)
$script:message=New-Object Windows.Forms.Label
$script:message.Text='Preparing Foliolet...'
$script:message.SetBounds(27,125,485,63)
$form.Controls.Add($script:message)
$script:bar=New-Object Windows.Forms.ProgressBar
$script:bar.SetBounds(27,191,485,8)
$script:bar.Style='Continuous'
$form.Controls.Add($script:bar)
function Make-Button([string]$Text,[int]$Left,[int]$Width) {
    $button=New-Object Windows.Forms.Button
    $button.Text=$Text
    $button.SetBounds($Left,220,$Width,36)
    $button.FlatStyle='Flat'
    $button.BackColor=[Drawing.Color]::White
    $form.Controls.Add($button)
    return $button
}
$script:open=Make-Button 'Open Foliolet' 27 162
$script:open.BackColor=[Drawing.ColorTranslator]::FromHtml('#573D85')
$script:open.ForeColor=[Drawing.Color]::White
$script:open.Enabled=$false
$script:action=Make-Button 'Stop Foliolet' 201 151
$script:action.Enabled=$false
$close=Make-Button 'Close' 364 148
$close.Add_Click({ $form.Close() })
$details=New-Object Windows.Forms.LinkLabel
$details.Text='View startup details'
$details.SetBounds(27,275,175,24)
$details.Add_LinkClicked({ Start-Process -FilePath explorer.exe -ArgumentList ('"'+$folioletData+'"') })
$form.Controls.Add($details)
$note=New-Object Windows.Forms.Label
$note.Text='Closing this window keeps Foliolet running.'
$note.Font=New-Object Drawing.Font('Segoe UI',9)
$note.ForeColor=[Drawing.Color]::DimGray
$note.SetBounds(27,301,490,22)
$form.Controls.Add($note)
function Open-Foliolet {
    Start-Process $folioletUrl
    $script:browserOpened=$true
}
$script:open.Add_Click({ Open-Foliolet })
function Begin-Worker([switch]$Stop) {
    $script:finished=$false; $script:finishedAt=$null
    $script:exitSeenAt=$null
    $script:uiExit=0
    $script:captured=$false
    $script:open.Enabled=$false; $script:action.Enabled=$false
    $script:message.Text=if ($Stop) { 'Stopping Foliolet...' } else { 'Starting Foliolet...' }
    $script:bar.Value=0
    if (-not $Stop -and (Test-Path -LiteralPath $script:uiStatus)) {
        $old=Read-FolioletJson $script:uiStatus
        if ($old.state -in @('starting','stopping')) {
            $oldProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$($old.worker)"
            if ($oldProcess -and $oldProcess.CommandLine -and $oldProcess.CommandLine.Contains((Join-Path $PSScriptRoot 'start-foliolet.ps1'))) {
                $script:worker=Get-Process -Id $old.worker
                return
            }
        }
    }
    $arguments=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(Join-Path $PSScriptRoot 'start-foliolet.ps1'),'-StatusPath',$script:uiStatus)
    if ($Stop) { $arguments+='-Stop' }
    $quoted=@($arguments | ForEach-Object { '"'+($_ -replace '"','\"')+'"' })
    $script:worker=Start-Process -FilePath (Get-FolioletPowerShell) -ArgumentList $quoted -WorkingDirectory $folioletRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $folioletData ('desktop-ui-worker-'+$PID+'.stdout.log')) -RedirectStandardError (Join-Path $folioletData ('desktop-ui-worker-'+$PID+'.stderr.log'))
}
$script:action.Add_Click({
    if ($script:action.Text -eq 'Stop Foliolet') { Begin-Worker -Stop }
    else { $script:browserOpened=$false; Begin-Worker }
})
$timer=New-Object Windows.Forms.Timer
$timer.Interval=500
$timer.Add_Tick({
    try {
        if (-not $script:worker) { return }
        if (-not $script:finished -and (Test-Path -LiteralPath $script:uiStatus)) {
            $state=Read-FolioletJson $script:uiStatus
            if ($state.worker -eq $script:worker.Id) {
                $script:message.Text=$state.message
                $script:bar.Value=[math]::Max(0,[math]::Min(100,[int]$state.progress))
                if ($state.state -in @('ready','error','stopped')) {
                    $script:finished=$true; $script:finishedAt=Get-Date
                    $script:open.Enabled=$state.state -eq 'ready'
                    $script:action.Enabled=$true
                    $script:action.Text=if ($state.state -eq 'ready') { 'Stop Foliolet' } else { 'Start again' }
                    if ($state.state -eq 'ready' -and -not $NoBrowser -and -not $script:browserOpened) { Open-Foliolet }
                    if ($state.state -eq 'error') { $script:uiExit=1 }
                    Write-FolioletJson (Join-Path $folioletData 'desktop-ui-result.json') @{state=$state.state;message=$state.message;browserOpened=$script:browserOpened;worker=$script:worker.Id;ui=$PID;noBrowser=[bool]$NoBrowser;updated=(Get-Date).ToUniversalTime().ToString('o')}
                }
            }
        }
        if (-not $script:finished -and $script:worker.HasExited) {
            # A child can publish its final status between the read above and this
            # process check. Give the next timer ticks time to consume that status.
            if (-not $script:exitSeenAt) { $script:exitSeenAt=Get-Date }
            elseif (((Get-Date)-$script:exitSeenAt).TotalSeconds -gt 2) {
                $script:message.Text='Startup did not finish. View startup details, then click Start again.'
                $script:action.Text='Start again'; $script:action.Enabled=$true
                $script:finished=$true; $script:finishedAt=Get-Date; $script:uiExit=1
            }
        }
        if ($CapturePath -and $script:finished -and -not $script:captured -and ((Get-Date)-$script:finishedAt).TotalSeconds -gt 0.5) {
            $capture=Assert-FolioletPath $CapturePath
            $bitmap=New-Object Drawing.Bitmap($form.Width,$form.Height)
            try { $form.DrawToBitmap($bitmap, (New-Object Drawing.Rectangle(0,0,$form.Width,$form.Height))); $bitmap.Save($capture,[Drawing.Imaging.ImageFormat]::Png) }
            finally { $bitmap.Dispose() }
            $script:captured=$true
        }
        if ($SmokeTest -and $script:finished -and ((Get-Date)-$script:finishedAt).TotalSeconds -gt 1) { $form.Close() }
    } catch {
        [IO.File]::WriteAllText((Join-Path $folioletData 'desktop-window-error.log'), ($_.Exception.ToString()+[Environment]::NewLine+$_.ScriptStackTrace))
        $script:message.Text='The launcher could not complete this step. View startup details for diagnostics.'
        $script:action.Text='Start again'; $script:action.Enabled=$true
        $script:uiExit=1
        if ($SmokeTest) { $form.Close() }
    }
})
$form.Add_Shown({ Begin-Worker; $timer.Start() })
try { $null=$form.ShowDialog() }
finally { $timer.Stop(); $timer.Dispose(); $form.Dispose(); $uiMutex.ReleaseMutex(); $uiMutex.Dispose() }
exit $script:uiExit
