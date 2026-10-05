param([switch]$ShowPanel, [switch]$ReduceMotion)
$ErrorActionPreference = 'Stop'
$lyaPython = Join-Path $PSScriptRoot '.venv-asr\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $lyaPython)) {
    throw 'Run the setup steps in desktop/README.md first.'
}
$lyaArguments = @(('"' + (Join-Path $PSScriptRoot 'tools\start_nvidia_lya.py') + '"'), '--gui', '--allow-nvidia-questions')
if ($ShowPanel) { $lyaArguments += '--show-panel' }
if ($ReduceMotion) { $lyaArguments += '--reduced-motion' }
Start-Process -FilePath $lyaPython -ArgumentList $lyaArguments -WorkingDirectory $PSScriptRoot -WindowStyle Normal -PassThru
