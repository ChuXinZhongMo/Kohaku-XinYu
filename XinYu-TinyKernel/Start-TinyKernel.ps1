param(
  [string]$HostAddress = "127.0.0.1",
  [int]$Port = 8877
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile = Join-Path $Root "state\tinykernel.pid"
$OutLog = Join-Path $Root "state\tinykernel-server.out.log"
$ErrLog = Join-Path $Root "state\tinykernel-server.err.log"

if (Test-Path -LiteralPath $PidFile) {
  $ExistingPid = Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue
  if ($ExistingPid -and (Get-Process -Id ([int]$ExistingPid) -ErrorAction SilentlyContinue)) {
    Write-Output "TinyKernel already running: pid=$ExistingPid"
    exit 0
  }
}

$WorkspacePython = Join-Path (Split-Path -Parent $Root) "Python312\python.exe"
if (Test-Path -LiteralPath $WorkspacePython) {
  $Python = $WorkspacePython
} else {
  $Python = "python"
}
$Args = @("server\app.py", "--host", $HostAddress, "--port", [string]$Port)
$Process = Start-Process -FilePath $Python -ArgumentList $Args -WorkingDirectory $Root -RedirectStandardOutput $OutLog -RedirectStandardError $ErrLog -WindowStyle Hidden -PassThru
$Process.Id | Set-Content -LiteralPath $PidFile -Encoding ASCII
Write-Output "TinyKernel started: pid=$($Process.Id) url=http://$HostAddress`:$Port"
