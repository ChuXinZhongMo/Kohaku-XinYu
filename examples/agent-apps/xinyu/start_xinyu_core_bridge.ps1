param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8765,
    [int]$TurnTimeoutSeconds = 165,
    [int]$SessionIdleTtlSeconds = 21600,
    [int]$MaxSessions = 8,
    [ValidateSet("always", "quality", "pressure", "off")]
    [string]$RendererMode = "off",
    [int]$AutonomousMaintenanceInitialDelaySeconds = 60,
    [int]$AutonomousMaintenanceIntervalSeconds = 1800,
    [int]$ProactiveMinIntervalSeconds = 1800,
    [string]$VenvPath = ".venv",
    [string]$BridgeToken = "",
    [switch]$RequireVersion,
    [switch]$ForceRestart,
    [switch]$AllowInsecureLlmHttp
)

$ErrorActionPreference = "Stop"

$xinyuDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $xinyuDir "$VenvPath\Scripts\python.exe"
$bridge = Join-Path $xinyuDir "xinyu_core_bridge.py"
$logDir = Join-Path $xinyuDir "logs"
$stdoutLog = Join-Path $logDir "xinyu_core_bridge.out.log"
$stderrLog = Join-Path $logDir "xinyu_core_bridge.err.log"

function Get-SourceBridgeVersion {
    $text = Get-Content -LiteralPath $bridge -Raw -Encoding UTF8
    $match = [regex]::Match($text, 'BRIDGE_VERSION\s*=\s*["'']([^"'']+)["'']')
    if (-not $match.Success) {
        throw "Could not read BRIDGE_VERSION from $bridge"
    }
    return $match.Groups[1].Value
}

function Get-RunningBridgeHealth {
    try {
        return Invoke-RestMethod -Uri "http://$HostAddress`:$Port/health" -Method Get -TimeoutSec 5
    } catch {
        return $null
    }
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Virtual environment Python not found: $venvPython"
}
if (-not (Test-Path -LiteralPath $bridge)) {
    throw "Bridge script not found: $bridge"
}
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$sourceVersion = Get-SourceBridgeVersion
$listener = Get-NetTCPConnection -LocalAddress $HostAddress -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $pidValue = [int]$listener.OwningProcess
    $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$pidValue" -ErrorAction SilentlyContinue
    $commandLine = if ($procInfo) { [string]$procInfo.CommandLine } else { "" }
    if ($commandLine -match "xinyu_core_bridge\.py") {
        if ($ForceRestart) {
            Write-Host "Stopping XinYu core bridge PID $pidValue for forced restart."
            Stop-Process -Id $pidValue -Force
            Start-Sleep -Seconds 2
        } elseif ($RequireVersion) {
            $health = Get-RunningBridgeHealth
            $runningVersion = if ($health) { [string]$health.version } else { "" }
            if ($runningVersion -ne $sourceVersion) {
                throw "Stale XinYu core bridge is listening on $HostAddress`:$Port. running=$runningVersion source=$sourceVersion. Use -ForceRestart or stop it first."
            }
            Write-Host "XinYu core bridge already listening with matching version $runningVersion. PID: $pidValue"
            exit 0
        } else {
            $health = Get-RunningBridgeHealth
            $runningVersion = if ($health) { [string]$health.version } else { "" }
            if ($runningVersion -ne $sourceVersion) {
                throw "Stale XinYu core bridge is listening on $HostAddress`:$Port. running=$runningVersion source=$sourceVersion. Use -ForceRestart or stop it first."
            }
            Write-Host "XinYu core bridge is already listening on $HostAddress`:$Port with version $runningVersion. PID: $pidValue"
            exit 0
        }
    } else {
        throw "Port $HostAddress`:$Port is occupied by another process. PID: $pidValue CommandLine: $commandLine"
    }
}

$args = @(
    $bridge,
    "--host", $HostAddress,
    "--port", "$Port",
    "--turn-timeout-seconds", "$TurnTimeoutSeconds",
    "--renderer-mode", "$RendererMode",
    "--session-idle-ttl-seconds", "$SessionIdleTtlSeconds",
    "--max-sessions", "$MaxSessions",
    "--autonomous-maintenance-initial-delay-seconds", "$AutonomousMaintenanceInitialDelaySeconds",
    "--autonomous-maintenance-interval-seconds", "$AutonomousMaintenanceIntervalSeconds",
    "--proactive-min-interval-seconds", "$ProactiveMinIntervalSeconds"
)
if ($BridgeToken) {
    $args += @("--bridge-token", $BridgeToken)
}

if ($AllowInsecureLlmHttp) {
    $env:XINYU_ALLOW_INSECURE_LLM_HTTP = "1"
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
    if ($RequireVersion -and [string]$health.version -ne $sourceVersion) {
        throw "Started bridge version mismatch: running=$($health.version) source=$sourceVersion"
    }
    $listener = Get-NetTCPConnection -LocalAddress $HostAddress -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    $listenerPid = if ($listener) { $listener.OwningProcess } else { "unknown" }
    $auto = $health.autonomous_maintenance
    Write-Host "XinYu core bridge started. launcher PID: $($process.Id), listener PID: $listenerPid"
    Write-Host "Health: ok=$($health.ok), sessions=$($health.sessions), autonomous=$($auto.enabled)/task=$($auto.task_running), url=http://$HostAddress`:$Port/chat"
    Write-Host "Logs: $stdoutLog"
} catch {
    Write-Host "XinYu core bridge process started but health check failed. PID: $($process.Id)"
    Write-Host "Check logs: $stdoutLog"
    Write-Host "Errors: $stderrLog"
}
