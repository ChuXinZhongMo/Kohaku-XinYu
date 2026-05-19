$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py = Join-Path $Root ".venv-train\Scripts\python.exe"

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
if (-not $env:HF_ENDPOINT) {
  $env:HF_ENDPOINT = "https://hf-mirror.com"
}

if (-not (Test-Path -LiteralPath $Py)) {
  throw "Training venv missing. Run .\Setup-TrainEnv.ps1 -Install first."
}

& $Py train\infer_lora.py
exit $LASTEXITCODE
