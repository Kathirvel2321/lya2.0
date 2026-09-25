param(
    [int]$Port = 8080,
    [int]$Threads = 6,
    [int]$Context = 2048
)

$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$model = Join-Path $project 'models/local/qwen3-4b-q4_k_m.gguf'
if (-not (Test-Path -LiteralPath $model)) {
    throw "Model is missing: $model"
}
$localRuntime = Join-Path $PSScriptRoot 'llama-runtime'
$server = Get-ChildItem $localRuntime -Filter 'llama-server.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $server) {
    $package = Get-ChildItem (Join-Path $env:LOCALAPPDATA 'Microsoft/WinGet/Packages') -Directory -Filter 'ggml.llamacpp_*' |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($package) { $server = Get-ChildItem $package.FullName -Recurse -Filter 'llama-server.exe' | Select-Object -First 1 }
}
if (-not $server) { throw 'llama-server.exe was not found in the installed package.' }

$args = @('-m', $model, '--host', '127.0.0.1', '--port', $Port,
    '--threads', $Threads, '--ctx-size', $Context, '--parallel', '1',
    '--alias', 'lya-local', '--device', 'none', '--no-op-offload',
    '--no-kv-offload')
Write-Host "Starting LYA local model at http://127.0.0.1:$Port/v1"
Write-Host "Model: $model"
& $server.FullName @args


