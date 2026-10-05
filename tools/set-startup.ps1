param([switch]$Disable, [switch]$OnlyIfExisting)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv-asr\Scripts\pythonw.exe'
$previousOnlinePythonPath = Join-Path $projectRoot '.venv-asr\Scripts\python.exe'
$legacyPythonPath = Join-Path $projectRoot '.venv-ui\Scripts\pythonw.exe'
$appPath = Join-Path $projectRoot 'tools\start_nvidia_lya.py'
if (!(Test-Path -LiteralPath $pythonPath) -or !(Test-Path -LiteralPath $appPath)) {
    throw 'LYA interpreter or desktop entry point is missing.'
}
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Startup')) 'LYA.lnk'
if ($OnlyIfExisting -and !(Test-Path -LiteralPath $shortcutPath)) {
    Write-Output 'No existing LYA startup shortcut; left disabled.'
    return
}
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
if ((Test-Path -LiteralPath $shortcutPath) -and $shortcut.TargetPath -notin @($pythonPath, $previousOnlinePythonPath, $legacyPythonPath)) {
    throw 'An unrelated LYA startup shortcut exists; it was not changed.'
}
if ($Disable) {
    if (Test-Path -LiteralPath $shortcutPath) { Remove-Item -LiteralPath $shortcutPath }
    Write-Output 'LYA automatic startup disabled.'
} else {
    $shortcut.TargetPath = $pythonPath
    $shortcut.Arguments = '"' + $appPath + '" --gui --allow-nvidia-questions'
    $shortcut.WorkingDirectory = $projectRoot
    $shortcut.WindowStyle = 1  # Native key dialog; pythonw has no console window.
    $shortcut.Description = 'LYA NVIDIA hearing at sign-in; session key required before listening'
    $shortcut.Save()
    Write-Output 'LYA automatic startup enabled for this Windows user.'
}
