$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = if (Test-Path -LiteralPath (Join-Path $ScriptDir "XinYu-Core")) {
  $ScriptDir
} else {
  Resolve-Path -LiteralPath (Join-Path $ScriptDir "..")
}
$TinyKernelRoot = Join-Path $Root "XinYu-TinyKernel"
$StopScript = Join-Path $TinyKernelRoot "Stop-TinyKernel.ps1"

if (-not (Test-Path -LiteralPath $StopScript)) {
  throw "TinyKernel stop script not found: $StopScript"
}

& $StopScript
