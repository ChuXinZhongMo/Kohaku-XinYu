param(
  [string]$Python = "",
  [switch]$Install
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent $Root
$Venv = Join-Path $Root ".venv-train"
$Py = Join-Path $Venv "Scripts\python.exe"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

if (-not $Python) {
  $Python = @(
    (Join-Path $WorkspaceRoot "runtime\deps\Python312\python.exe"),
    (Join-Path $WorkspaceRoot "Python312\python.exe")
  ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}

if (-not (Test-Path -LiteralPath $Python)) {
  throw "Python not found: $Python"
}

if (-not (Test-Path -LiteralPath $Py)) {
  & $Python -m venv $Venv
}

& $Py -m pip install --upgrade pip setuptools wheel

if ($Install) {
  # Official PyTorch Windows pip wheels are selected by CUDA build. This project
  # uses cu128 as the conservative CUDA 12.x target for the GTX 1660 Ti machine.
  & $Py -m pip install torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
  & $Py -m pip install -r (Join-Path $Root "requirements-train.txt")
}

& $Py --version
Write-Output "train_env_python=$Py"
