$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile = Join-Path $Root "state\tinykernel.pid"

if (-not (Test-Path -LiteralPath $PidFile)) {
  Write-Output "TinyKernel pid file not found."
  exit 0
}

$PidValue = Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue
if ($PidValue) {
  $Process = Get-Process -Id ([int]$PidValue) -ErrorAction SilentlyContinue
  if ($Process) {
    Stop-Process -Id $Process.Id
    Write-Output "TinyKernel stopped: pid=$PidValue"
  } else {
    Write-Output "TinyKernel process already stopped: pid=$PidValue"
  }
}
Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
