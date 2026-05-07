param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 6199,
    [string]$CoreUrl = "http://127.0.0.1:8765/chat",
    [string]$ConfigPath = "xinyu_qq_gateway.config.json",
    [string]$VenvPath = ".venv",
    [string]$BridgeToken = "",
    [int]$RestartDrainTimeoutSeconds = 180,
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

function Import-LocalEnv {
    $envPath = Join-Path $xinyuDir "xinyu.local.env"
    if (-not (Test-Path -LiteralPath $envPath)) {
        return
    }
    foreach ($rawLine in Get-Content -LiteralPath $envPath -Encoding UTF8) {
        $line = $rawLine.Trim()
        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            continue
        }
        $parts = $line.Split("=", 2)
        $key = $parts[0].Trim()
        $value = $parts[1].Trim().Trim('"').Trim("'")
        if ([string]::IsNullOrWhiteSpace($key)) {
            continue
        }
        if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($key, "Process"))) {
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

function Resolve-BridgeToken {
    if (-not [string]::IsNullOrWhiteSpace($BridgeToken)) {
        return $BridgeToken.Trim()
    }
    if (-not [string]::IsNullOrWhiteSpace($env:XINYU_BRIDGE_TOKEN)) {
        return $env:XINYU_BRIDGE_TOKEN.Trim()
    }
    $candidateDirs = New-Object System.Collections.Generic.List[string]
    $cursor = Get-Item -LiteralPath $xinyuDir
    $candidateDirs.Add($cursor.FullName)
    for ($i = 0; $i -lt 4 -and $null -ne $cursor.Parent; $i++) {
        $cursor = $cursor.Parent
        $candidateDirs.Add($cursor.FullName)
    }
    foreach ($dir in $candidateDirs) {
        $tokenPath = Join-Path $dir ".xinyu_bridge_token"
        if (Test-Path -LiteralPath $tokenPath) {
            $token = (Get-Content -LiteralPath $tokenPath -Raw -Encoding UTF8).Trim()
            if (-not [string]::IsNullOrWhiteSpace($token)) {
                return $token
            }
        }
    }
    return ""
}

function Get-CoreHealthUrl {
    try {
        $builder = [System.UriBuilder]::new($CoreUrl)
        $builder.Path = "/health"
        $builder.Query = ""
        return $builder.Uri.AbsoluteUri
    } catch {
        return ""
    }
}

function Wait-CoreTurnIdleBeforeGatewayStop {
    param([int]$TimeoutSeconds)
    if ($TimeoutSeconds -le 0) {
        return
    }
    $healthUrl = Get-CoreHealthUrl
    if ([string]::IsNullOrWhiteSpace($healthUrl)) {
        return
    }
    $deadline = (Get-Date).AddSeconds([Math]::Max(1, $TimeoutSeconds))
    $reported = $false
    while ((Get-Date) -lt $deadline) {
        try {
            $health = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 5
            $presence = $health.runtime_presence
            $turnState = if ($presence) { [string]$presence.current_turn_state } else { "" }
            if ($turnState -ne "running" -and $turnState -ne "starting") {
                if ($reported) {
                    Write-Host "Core turn state is idle before gateway restart: $turnState"
                }
                Start-Sleep -Seconds 3
                return
            }
            if (-not $reported) {
                Write-Host "Waiting for in-flight core turn before restarting QQ gateway."
                $reported = $true
            }
        } catch {
            return
        }
        Start-Sleep -Seconds 1
    }
    Write-Host "Core turn did not become idle within $TimeoutSeconds seconds; continuing gateway restart."
}

function Stop-GatewayProcessFamily {
    param(
        [int]$ListenerPid,
        [string]$ScriptPattern
    )
    $ids = New-Object System.Collections.Generic.List[int]
    $listenerInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$ListenerPid" -ErrorAction SilentlyContinue
    if ($listenerInfo) {
        $parentId = [int]$listenerInfo.ParentProcessId
        if ($parentId -gt 0) {
            $parentInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$parentId" -ErrorAction SilentlyContinue
            if ($parentInfo -and [string]$parentInfo.CommandLine -match $ScriptPattern) {
                $ids.Add($parentId)
            }
        }
    }
    $ids.Add($ListenerPid)
    foreach ($id in ($ids | Select-Object -Unique)) {
        Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
    }
}

Import-LocalEnv

$listener = Get-NetTCPConnection -LocalAddress $HostAddress -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $pidValue = [int]$listener.OwningProcess
    $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$pidValue" -ErrorAction SilentlyContinue
    $commandLine = if ($procInfo) { [string]$procInfo.CommandLine } else { "" }
    if ($commandLine -match "xinyu_qq_gateway\.py") {
        if ($ForceRestart) {
            Wait-CoreTurnIdleBeforeGatewayStop -TimeoutSeconds $RestartDrainTimeoutSeconds
            Write-Host "Stopping existing XinYu QQ gateway PID $pidValue."
            Stop-GatewayProcessFamily -ListenerPid $pidValue -ScriptPattern "xinyu_qq_gateway\.py"
            Start-Sleep -Seconds 1
        } else {
            Write-Host "XinYu QQ gateway is already listening on $HostAddress`:$Port. PID: $pidValue"
            exit 0
        }
    } else {
        throw "Port $HostAddress`:$Port is occupied by another process. PID: $pidValue CommandLine: $commandLine"
    }
}

$effectiveBridgeToken = Resolve-BridgeToken
$args = @(
    $gateway,
    "--config", $config,
    "--host", $HostAddress,
    "--port", "$Port",
    "--core-url", $CoreUrl
)
if ($effectiveBridgeToken) {
    $args += @("--bridge-token", $effectiveBridgeToken)
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
    throw "XinYu QQ gateway failed to listen on $HostAddress`:$Port after startup."
}
