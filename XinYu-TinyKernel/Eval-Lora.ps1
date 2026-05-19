$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py = Join-Path $Root ".venv-train\Scripts\python.exe"

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
if (-not $env:HF_ENDPOINT) {
  $env:HF_ENDPOINT = "https://hf-mirror.com"
}

& $Py eval\eval_lora.py
exit $LASTEXITCODE
