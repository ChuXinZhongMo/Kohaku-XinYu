param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 6199,
    [string]$CoreUrl = "http://127.0.0.1:8765/chat",
    [string]$ConfigPath = "xinyu_qq_gateway.config.json",
    [string]$VenvPath = ".venv",
    [string]$BridgeToken = "",
    [switch]$ForceRestart
)

$ErrorActionPreference = "Stop"

$xinyuDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $xinyuDir "$VenvPath\Scripts\python.exe"
$gateway = Join-Path $xinyuDir "xinyu_qq_gateway.py"
$config = if ([System.IO.Path]::IsPathRooted($ConfigPath)) { $ConfigPath } else { Join-Path $xinyuDir $ConfigPath }
$logDir = Join-Path $xinyuDir "logs"
$stdoutLog = Join-Path $logDir "xinyu_qq_gateway.out.log"
$stderrLog = Join-Path $logDir "xinyu_qq_gateway.err.log"

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Virtual environment Python not found: $venvPython"
}
if (-not (Test-Path -LiteralPath $gateway)) {
    throw "QQ gateway script not found: $gateway"
}
if (-not (Test-Path -LiteralPath $config)) {
    throw "QQ gateway config not found: $config"
}
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$listener = Get-NetTCPConnection -LocalAddress $HostAddress -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $pidValue = [int]$listener.OwningProcess
    $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$pidValue" -ErrorAction SilentlyContinue
    $commandLine = if ($procInfo) { [string]$procInfo.CommandLine } else { "" }
    if ($commandLine -match "xinyu_qq_gateway\.py") {
        if ($ForceRestart) {
            Write-Host "Stopping existing XinYu QQ gateway PID $pidValue."
            Stop-Process -Id $pidValue -Force
            Start-Sleep -Seconds 1
        } else {
            Write-Host "XinYu QQ gateway is already listening on $HostAddress`:$Port. PID: $pidValue"
            exit 0
        }
    } else {
        throw "Port $HostAddress`:$Port is occupied by another process. PID: $pidValue CommandLine: $commandLine"
    }
}

$args = @(
    $gateway,
    "--config", $config,
    "--host", $HostAddress,
    "--port", "$Port",
    "--core-url", $CoreUrl
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

$listener = Get-NetTCPConnection -LocalAddress $HostAddress -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    Write-Host "XinYu QQ gateway started. launcher PID: $($process.Id), listener PID: $($listener.OwningProcess)"
    Write-Host "OneBot reverse WebSocket: ws://$HostAddress`:$Port/ws"
    Write-Host "Logs: $stdoutLog"
} else {
    Write-Host "XinYu QQ gateway process started but port check failed. PID: $($process.Id)"
    Write-Host "Check logs: $stdoutLog"
    Write-Host "Errors: $stderrLog"
}
