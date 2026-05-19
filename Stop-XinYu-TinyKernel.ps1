$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$TinyKernelRoot = Join-Path $Root "XinYu-TinyKernel"
$StopScript = Join-Path $TinyKernelRoot "Stop-TinyKernel.ps1"

if (-not (Test-Path -LiteralPath $StopScript)) {
  throw "TinyKernel stop script not found: $StopScript"
}

& $StopScript
