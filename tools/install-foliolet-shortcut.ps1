$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'foliolet-desktop-common.ps1')
$desktop=[Environment]::GetFolderPath('Desktop')
$shortcutPath=Join-Path $desktop 'Foliolet.lnk'
$shell=New-Object -ComObject WScript.Shell
if (Test-Path -LiteralPath $shortcutPath) {
    $existing=$shell.CreateShortcut($shortcutPath)
    if (-not $existing.Arguments.Contains($folioletRoot)) {
        $shortcutPath=Join-Path $desktop 'Foliolet Assisted.lnk'
        if (Test-Path -LiteralPath $shortcutPath) {
            $existing=$shell.CreateShortcut($shortcutPath)
            if (-not $existing.Arguments.Contains($folioletRoot)) { throw 'Both Foliolet shortcut names are already used by another application; neither was overwritten.' }
        }
    }
}
$shortcut=$shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$shortcut.Arguments='-NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -File "'+(Join-Path $PSScriptRoot 'launch-foliolet.ps1')+'"'
$shortcut.WorkingDirectory=$folioletRoot
$shortcut.Description='Start Foliolet and its local services, then open your workspace.'
$shortcut.IconLocation=(Join-Path $env:SystemRoot 'System32\shell32.dll')+',14'
$shortcut.WindowStyle=7
$shortcut.Save()
Write-Output ('Ready: double-click ' + $shortcutPath)
