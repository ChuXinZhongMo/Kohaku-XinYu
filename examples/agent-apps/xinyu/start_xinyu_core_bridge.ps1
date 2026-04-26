param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8765,
    [int]$TurnTimeoutSeconds = 165,
    [int]$SessionIdleTtlSeconds = 21600,
    [int]$MaxSessions = 8,
    [string]$VenvPath = ".venv",
    [string]$BridgeToken = ""
)

$ErrorActionPreference = "Stop"

$xinyuDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $xinyuDir "$VenvPath\Scripts\python.exe"
$bridge = Join-Path $xinyuDir "xinyu_core_bridge.py"
$logDir = Join-Path $xinyuDir "logs"
$stdoutLog = Join-Path $logDir "xinyu_core_bridge.out.log"
$stderrLog = Join-Path $logDir "xinyu_core_bridge.err.log"

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Virtual environment Python not found: $venvPython"
}
if (-not (Test-Path -LiteralPath $bridge)) {
    throw "Bridge script not found: $bridge"
}
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$listener = Get-NetTCPConnection -LocalAddress $HostAddress -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $pidValue = [int]$listener.OwningProcess
    $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$pidValue" -ErrorAction SilentlyContinue
    $commandLine = if ($procInfo) { [string]$procInfo.CommandLine } else { "" }
    if ($commandLine -match "xinyu_core_bridge\.py") {
        Write-Host "XinYu core bridge is already listening on $HostAddress`:$Port. PID: $pidValue"
    } else {
        throw "Port $HostAddress`:$Port is occupied by another process. PID: $pidValue CommandLine: $commandLine"
    }
    exit 0
}

$args = @(
    $bridge,
    "--host", $HostAddress,
    "--port", "$Port",
    "--turn-timeout-seconds", "$TurnTimeoutSeconds",
    "--session-idle-ttl-seconds", "$SessionIdleTtlSeconds",
    "--max-sessions", "$MaxSessions"
)
if ($BridgeToken) {
    $args += @("--bridge-token", $BridgeToken)
}

$process = Start-Process `
    -FilePath $venvPython `
    -ArgumentList $args `
    -WorkingDirectory $xinyuDir `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -WindowStyle Hidden `
    -PassThru

Start-Sleep -Seconds 2

try {
    $health = Invoke-RestMethod -Uri "http://$HostAddress`:$Port/health" -Method Get -TimeoutSec 5
    $listener = Get-NetTCPConnection -LocalAddress $HostAddress -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    $listenerPid = if ($listener) { $listener.OwningProcess } else { "unknown" }
    Write-Host "XinYu core bridge started. launcher PID: $($process.Id), listener PID: $listenerPid"
    Write-Host "Health: ok=$($health.ok), sessions=$($health.sessions), url=http://$HostAddress`:$Port/chat"
    Write-Host "Logs: $stdoutLog"
} catch {
    Write-Host "XinYu core bridge process started but health check failed. PID: $($process.Id)"
    Write-Host "Check logs: $stdoutLog"
    Write-Host "Errors: $stderrLog"
}
