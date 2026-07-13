param(
    [switch]$OpenDashboards,
    [switch]$StrictLlmHttps,
    [switch]$ForceGatewayRestart,
    [ValidateSet("Normal", "Minimized", "Hidden")]
    [string]$NapCatConsoleWindowStyle = "Normal"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = if (Test-Path -LiteralPath (Join-Path $ScriptDir "XinYu-Core")) {
    $ScriptDir
} else {
    Resolve-Path -LiteralPath (Join-Path $ScriptDir "..")
}
$CoreDir = Join-Path $Root "XinYu-Core\examples\agent-apps\xinyu"
$NapCatDirCandidates = @(
    (Join-Path $Root "runtime\deps\NapCatQQ\NapCat.44498.Shell"),
    (Join-Path $Root "NapCatQQ\NapCat.44498.Shell")
)
$NapCatDir = $NapCatDirCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $NapCatDir) {
    $NapCatDir = $NapCatDirCandidates[0]
}

$CoreStart = Join-Path $CoreDir "start_xinyu_core_bridge.ps1"
$GatewayStart = Join-Path $CoreDir "start_xinyu_qq_gateway.ps1"
$NapCatBat = Join-Path $NapCatDir "napcat.bat"
$TinyKernelStart = Join-Path $Root "scripts\Start-XinYu-TinyKernel.ps1"

function Test-HttpOk {
    param(
        [string]$Uri,
        [int]$TimeoutSec = 3,
        [hashtable]$Headers = @{}
    )
    try {
        if ($Headers.Count -gt 0) {
            $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec $TimeoutSec -Headers $Headers
        } else {
            $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec $TimeoutSec
        }
        return [int]$response.StatusCode -ge 200 -and [int]$response.StatusCode -lt 400
    } catch {
        return $false
    }
}

function Test-ListeningPort {
    param([int]$Port)
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    return $null -ne $listener
}

function Get-ListeningProcessCommandLine {
    param([int]$Port)
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $listener) {
        return ""
    }
    $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$listener.OwningProcess)" -ErrorAction SilentlyContinue
    if ($procInfo) {
        return [string]$procInfo.CommandLine
    }
    return ""
}

function Wait-Until {
    param(
        [scriptblock]$Condition,
        [int]$TimeoutSeconds,
        [string]$Label
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (& $Condition) {
            Write-Host "[ok] $Label"
            return $true
        }
        Start-Sleep -Seconds 1
    }
    Write-Host "[warn] $Label did not become ready within ${TimeoutSeconds}s"
    return $false
}

function Require-Until {
    param(
        [scriptblock]$Condition,
        [int]$TimeoutSeconds,
        [string]$Label,
        [string]$FailureMessage
    )
    if (-not (Wait-Until -Condition $Condition -TimeoutSeconds $TimeoutSeconds -Label $Label)) {
        throw $FailureMessage
    }
}

function Ensure-Dir {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Get-OrCreate-BridgeToken {
    param([string]$Path)
    if ($env:XINYU_BRIDGE_TOKEN) {
        return [string]$env:XINYU_BRIDGE_TOKEN
    }
    if (Test-Path -LiteralPath $Path) {
        $existing = (Get-Content -LiteralPath $Path -Raw -Encoding ASCII).Trim()
        if ($existing) {
            return $existing
        }
    }
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    } finally {
        $rng.Dispose()
    }
    $token = [Convert]::ToBase64String($bytes)
    Set-Content -LiteralPath $Path -Value $token -Encoding ASCII
    return $token
}

function Get-BridgeHeaders {
    if ($BridgeToken) {
        return @{ "X-XinYu-Bridge-Token" = $BridgeToken }
    }
    return @{}
}

function Test-CodexBridgeTokenReady {
    param([string]$Token)
    if (-not $Token) {
        return $false
    }
    try {
        Invoke-WebRequest `
            -Uri "http://127.0.0.1:8765/codex/execute" `
            -Method Post `
            -UseBasicParsing `
            -TimeoutSec 5 `
            -ContentType "application/json; charset=utf-8" `
            -Headers @{ "X-XinYu-Bridge-Token" = $Token } `
            -Body "{}" | Out-Null
        return $true
    } catch {
        $response = $_.Exception.Response
        if ($response -and [int]$response.StatusCode -eq 400) {
            return $true
        }
        return $false
    }
}

function Get-CoreSourceVersion {
    $bridge = Join-Path $CoreDir "xinyu_core_bridge.py"
    $text = Get-Content -LiteralPath $bridge -Raw -Encoding UTF8
    $match = [regex]::Match($text, 'BRIDGE_VERSION\s*=\s*["'']([^"'']+)["'']')
    if ($match.Success) {
        return $match.Groups[1].Value
    }
    return ""
}

function Get-CoreHealth {
    try {
        return Invoke-RestMethod -Uri "http://127.0.0.1:8765/health" -Method Get -TimeoutSec 5
    } catch {
        return $null
    }
}

Write-Host "=== XinYu QQ one-click startup ==="
Write-Host "Root: $Root"

$BridgeTokenPath = Join-Path $Root ".xinyu_bridge_token"
$BridgeToken = Get-OrCreate-BridgeToken -Path $BridgeTokenPath
$env:XINYU_BRIDGE_TOKEN = $BridgeToken

if (-not (Test-Path -LiteralPath $CoreStart)) {
    throw "XinYu core start script not found: $CoreStart"
}
if (-not (Test-Path -LiteralPath $GatewayStart)) {
    throw "XinYu QQ gateway start script not found: $GatewayStart"
}
if (-not (Test-Path -LiteralPath $NapCatBat)) {
    throw "NapCat start script not found: $NapCatBat"
}

Write-Host "`n[0/4] XinYu TinyKernel shadow"
if (Test-ListeningPort 8877) {
    Write-Host "[ok] TinyKernel already running: http://127.0.0.1:8877"
} elseif (Test-Path -LiteralPath $TinyKernelStart) {
    & $TinyKernelStart
    Start-Sleep -Seconds 2
    if (Test-ListeningPort 8877) {
        Write-Host "[ok] TinyKernel started: http://127.0.0.1:8877"
    } else {
        Write-Host "[warn] TinyKernel did not start on port 8877 — shadow log will be unavailable"
    }
} else {
    Write-Host "[skip] TinyKernel start script not found: $TinyKernelStart"
}

Write-Host "`n[1/4] XinYu core bridge"
$coreHealth = Get-CoreHealth
$coreAlreadyRunning = $null -ne $coreHealth
$coreSourceVersion = Get-CoreSourceVersion
$coreRunningVersion = if ($coreHealth) { [string]$coreHealth.version } else { "" }
$coreVersionStale = $coreAlreadyRunning -and $coreSourceVersion -and ($coreRunningVersion -ne $coreSourceVersion)
$coreTokenNotReady = $coreAlreadyRunning -and -not (Test-CodexBridgeTokenReady -Token $BridgeToken)
if ($coreVersionStale -or $coreTokenNotReady) {
    if ($coreVersionStale) {
        Write-Host "[restart] XinYu core bridge version drift: running=$coreRunningVersion source=$coreSourceVersion"
    } else {
        Write-Host "[restart] XinYu core bridge is running without the current Codex bridge token."
    }
    Push-Location $CoreDir
    try {
        if ($StrictLlmHttps) {
            & $CoreStart -Port 8765 -ForceRestart
        } else {
            & $CoreStart -Port 8765 -ForceRestart -AllowInsecureLlmHttp
        }
    } finally {
        Pop-Location
    }
} elseif ($coreAlreadyRunning) {
    Write-Host "[ok] XinYu core bridge already running: http://127.0.0.1:8765"
} else {
    Push-Location $CoreDir
    try {
        if ($StrictLlmHttps) {
            & $CoreStart -Port 8765
        } else {
            & $CoreStart -Port 8765 -AllowInsecureLlmHttp
        }
    } finally {
        Pop-Location
    }
}
Require-Until -TimeoutSeconds 20 -Label "XinYu core bridge health" -FailureMessage "XinYu core bridge health check failed. Check core logs under $CoreDir\logs." -Condition {
    Test-HttpOk "http://127.0.0.1:8765/health"
}
Require-Until -TimeoutSeconds 10 -Label "XinYu no-memory probe" -FailureMessage "XinYu core bridge probe failed. The bridge is listening but not handling requests correctly." -Condition {
    Test-HttpOk "http://127.0.0.1:8765/probe?text=startup" -Headers (Get-BridgeHeaders)
}

Write-Host "`n[2/4] XinYu native QQ gateway"
if (Test-ListeningPort 6199) {
    $gatewayCommandLine = Get-ListeningProcessCommandLine 6199
    if ($gatewayCommandLine -match "xinyu_qq_gateway\.py") {
        if ($ForceGatewayRestart) {
            Write-Host "[restart] XinYu QQ gateway already listening; restarting by request."
            Push-Location $CoreDir
            try {
                & $GatewayStart -HostAddress "127.0.0.1" -Port 6199 -CoreUrl "http://127.0.0.1:8765/chat" -BridgeToken $BridgeToken -ForceRestart
            } finally {
                Pop-Location
            }
        } else {
            Write-Host "[ok] XinYu QQ gateway already running: ws://127.0.0.1:6199/ws"
        }
    } else {
        throw "Port 6199 is already occupied by a non-XinYu gateway process: $gatewayCommandLine"
    }
} else {
    Push-Location $CoreDir
    try {
        & $GatewayStart -HostAddress "127.0.0.1" -Port 6199 -CoreUrl "http://127.0.0.1:8765/chat" -BridgeToken $BridgeToken
    } finally {
        Pop-Location
    }
}
Require-Until -TimeoutSeconds 45 -Label "XinYu QQ gateway OneBot server 6199" -FailureMessage "XinYu QQ gateway did not start on port 6199. Check gateway logs under $CoreDir\logs." -Condition {
    Test-ListeningPort 6199
}

Write-Host "`n[3/4] NapCat QQ"
if (Test-HttpOk "http://127.0.0.1:6099/webui/") {
    Write-Host "[ok] NapCat WebUI already running: http://127.0.0.1:6099/webui/"
} else {
    $napCatBatFull = "`"$NapCatBat`""
    $cmdVerb = if ($NapCatConsoleWindowStyle -eq "Hidden") { "/c" } else { "/k" }
    Start-Process `
        -FilePath "C:\Windows\System32\cmd.exe" `
        -ArgumentList "$cmdVerb $napCatBatFull" `
        -WorkingDirectory $NapCatDir `
        -WindowStyle $NapCatConsoleWindowStyle
    Write-Host "[start] NapCat visible window requested"
}
Require-Until -TimeoutSeconds 45 -Label "NapCat WebUI 6099" -FailureMessage "NapCat WebUI did not become ready on port 6099. Finish QQ/NapCat startup, then run this script again." -Condition {
    Test-HttpOk "http://127.0.0.1:6099/webui/"
}

Require-Until -TimeoutSeconds 60 -Label "NapCat -> XinYu QQ gateway WebSocket" -FailureMessage "NapCat did not establish the OneBot reverse WebSocket to XinYu gateway. Check NapCat login and reverse WebSocket config: ws://127.0.0.1:6199/ws" -Condition {
    $connection = Get-NetTCPConnection -LocalPort 6199 -State Established -ErrorAction SilentlyContinue |
        Where-Object { $_.RemoteAddress -eq "127.0.0.1" } |
        Select-Object -First 1
    return $null -ne $connection
}

Write-Host "`n[4/4] Verify"
Write-Host "`n=== URLs ==="
Write-Host "TinyKernel:    http://127.0.0.1:8877"
Write-Host "NapCat:        http://127.0.0.1:6099/webui/"
Write-Host "XinYu Core:    http://127.0.0.1:8765/health"
Write-Host "XinYu QQ WS:   ws://127.0.0.1:6199/ws"

if ($OpenDashboards) {
    Start-Process "http://127.0.0.1:6099/webui/"
}

Write-Host "`nDone. Send a private QQ message to the whitelisted owner account to test XinYu."
