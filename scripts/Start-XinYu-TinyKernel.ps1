param(
  [string]$HostAddress = "127.0.0.1",
  [int]$Port = 8877
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = if (Test-Path -LiteralPath (Join-Path $ScriptDir "XinYu-Core")) {
  $ScriptDir
} else {
  Resolve-Path -LiteralPath (Join-Path $ScriptDir "..")
}
$TinyKernelRoot = Join-Path $Root "XinYu-TinyKernel"
$StartScript = Join-Path $TinyKernelRoot "Start-TinyKernel.ps1"

if (-not (Test-Path -LiteralPath $StartScript)) {
  throw "TinyKernel start script not found: $StartScript"
}

& $StartScript -HostAddress $HostAddress -Port $Port
