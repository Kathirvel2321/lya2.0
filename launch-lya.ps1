param([switch]$ShowPanel, [switch]$ReduceMotion)
$ErrorActionPreference = 'Stop'
$lyaPython = Join-Path $PSScriptRoot '.venv-ui\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $lyaPython)) {
    throw 'Run the setup steps in desktop/README.md first.'
}
$lyaArguments = @(('"' + (Join-Path $PSScriptRoot 'desktop\app.py') + '"'))
if ($ShowPanel) { $lyaArguments += '--show-panel' }
if ($ReduceMotion) { $lyaArguments += '--reduced-motion' }
Start-Process -FilePath $lyaPython -ArgumentList $lyaArguments -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru
