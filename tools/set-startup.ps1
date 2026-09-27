param([switch]$Disable)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv-ui\Scripts\pythonw.exe'
$appPath = Join-Path $projectRoot 'desktop\app.py'
if (!(Test-Path -LiteralPath $pythonPath) -or !(Test-Path -LiteralPath $appPath)) {
    throw 'LYA interpreter or desktop entry point is missing.'
}
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Startup')) 'LYA.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
if ((Test-Path -LiteralPath $shortcutPath) -and $shortcut.TargetPath -ne $pythonPath) {
    throw 'An unrelated LYA startup shortcut exists; it was not changed.'
}
if ($Disable) {
    if (Test-Path -LiteralPath $shortcutPath) { Remove-Item -LiteralPath $shortcutPath }
    Write-Output 'LYA automatic startup disabled.'
} else {
    $shortcut.TargetPath = $pythonPath
    $shortcut.Arguments = '"' + $appPath + '" --skip-setup'
    $shortcut.WorkingDirectory = $projectRoot
    $shortcut.Description = 'LYA local name and two-clap listener at Windows sign-in'
    $shortcut.Save()
    Write-Output 'LYA automatic startup enabled for this Windows user.'
}
