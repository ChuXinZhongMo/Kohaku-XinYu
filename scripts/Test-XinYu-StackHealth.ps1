<#
.SYNOPSIS
  Read-only health check for the XinYu QQ delivery stack.

.DESCRIPTION
  Checks:
  - core bridge HTTP health on :8765
  - QQ gateway listening on :6199
  - NapCat reverse-WS Established count on :6199
  - QQ outbox backlog (queued/claimed) under the app runtime

  Does not start or stop processes. For start use:
    .\XinYu.ps1 start qq
  Docs: docs/system/NAPCAT-GATEWAY-OPERATOR.md

.PARAMETER CorePort
  Core bridge port (default 8765).

.PARAMETER GatewayPort
  QQ gateway OneBot reverse WS port (default 6199).

.PARAMETER Strict
  Exit 1 if any required check fails (bridge/gateway/NapCat WS/outbox backlog).

.EXAMPLE
  .\scripts\Test-XinYu-StackHealth.ps1

.EXAMPLE
  .\scripts\Test-XinYu-StackHealth.ps1 -Strict
#>
[CmdletBinding()]
param(
    [int]$CorePort = 8765,
    [int]$GatewayPort = 6199,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = if (Test-Path -LiteralPath (Join-Path $ScriptDir "XinYu-Core")) {
    $ScriptDir
} else {
    (Resolve-Path -LiteralPath (Join-Path $ScriptDir "..")).Path
}
$AppRoot = Join-Path $Root "XinYu-Core\examples\agent-apps\xinyu"
$OutboxPath = Join-Path $AppRoot "memory\context\qq_outbox_queue.json"
$OutboxHelper = Join-Path $AppRoot "tools\outbox_summary.py"
$PythonCandidates = @(
    (Join-Path $AppRoot ".venv\Scripts\python.exe"),
    (Join-Path $Root "runtime\deps\Python312\python.exe"),
    "python"
)

function Write-Check {
    param(
        [ValidateSet("ok", "warn", "fail", "info")]
        [string]$Level,
        [string]$Message
    )
    $color = switch ($Level) {
        "ok" { "Green" }
        "warn" { "Yellow" }
        "fail" { "Red" }
        default { "Gray" }
    }
    Write-Host ("[{0}] {1}" -f $Level.ToUpperInvariant(), $Message) -ForegroundColor $color
}

function Test-ListeningPort {
    param([int]$Port)
    $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)
}

function Get-EstablishedCount {
    param([int]$Port)
    @(Get-NetTCPConnection -LocalPort $Port -State Established -ErrorAction SilentlyContinue).Count
}

function Get-CoreHealth {
    try {
        return Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/health" -f $CorePort) -Method Get -TimeoutSec 4
    } catch {
        return $null
    }
}

function Resolve-Python {
    foreach ($candidate in $PythonCandidates) {
        if ($candidate -eq "python") {
            $cmd = Get-Command python -ErrorAction SilentlyContinue
            if ($cmd) { return $cmd.Source }
            continue
        }
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    return $null
}

function Get-OutboxSummary {
    param([string]$Path, [string]$PythonExe, [string]$HelperScript)
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    if (-not $PythonExe) {
        return @{ error = "python_not_found" }
    }
    if (-not (Test-Path -LiteralPath $HelperScript)) {
        return @{ error = "helper_missing" }
    }
    try {
        $json = & $PythonExe $HelperScript $Path 2>$null
        if (-not $json) { return @{ error = "parse_failed" } }
        return ($json | ConvertFrom-Json)
    } catch {
        return @{ error = $_.Exception.Message }
    }
}

Write-Host "XinYu stack health (read-only)" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host "App:  $AppRoot"
Write-Host ""

$failures = New-Object System.Collections.Generic.List[string]
$warnings = New-Object System.Collections.Generic.List[string]

# 1) Core bridge
$health = Get-CoreHealth
if ($null -eq $health) {
    Write-Check fail ("core bridge not healthy on :{0}" -f $CorePort)
    [void]$failures.Add("core_bridge")
} else {
    $ver = [string]$health.version
    $sessions = $health.sessions
    Write-Check ok ("core bridge :{0} version={1} sessions={2}" -f $CorePort, $ver, $sessions)
}

# 2) Gateway listen
if (Test-ListeningPort $GatewayPort) {
    Write-Check ok ("qq gateway listening on :{0}" -f $GatewayPort)
} else {
    Write-Check fail ("qq gateway not listening on :{0}" -f $GatewayPort)
    [void]$failures.Add("qq_gateway_listen")
}

# 3) NapCat reverse WS established
$estab = Get-EstablishedCount -Port $GatewayPort
if ($estab -gt 0) {
    Write-Check ok ("NapCat reverse WS Established={0} on :{1}" -f $estab, $GatewayPort)
} else {
    Write-Check fail ("no Established connections on :{0} (start NapCat reverse client)" -f $GatewayPort)
    [void]$failures.Add("napcat_ws")
    Write-Check info "See docs/system/NAPCAT-GATEWAY-OPERATOR.md"
}

# 4) Outbox
$py = Resolve-Python
$summary = Get-OutboxSummary -Path $OutboxPath -PythonExe $py -HelperScript $OutboxHelper
if ($null -eq $summary) {
    Write-Check warn "qq outbox file missing (no backlog yet)"
    [void]$warnings.Add("outbox_missing")
} elseif ($summary.error) {
    Write-Check warn ("qq outbox unreadable: {0}" -f $summary.error)
    [void]$warnings.Add("outbox_unreadable")
} else {
    $counts = $summary.counts
    $queued = 0
    $claimed = 0
    if ($counts.PSObject.Properties.Name -contains "queued") { $queued = [int]$counts.queued }
    if ($counts.PSObject.Properties.Name -contains "claimed") { $claimed = [int]$counts.claimed }
    $parts = @()
    foreach ($p in $counts.PSObject.Properties) {
        $parts += ("{0}={1}" -f $p.Name, $p.Value)
    }
    Write-Check info ("qq outbox total={0} {1}" -f $summary.total, ($parts -join " "))
    if (($queued + $claimed) -gt 0 -and $estab -eq 0) {
        Write-Check warn ("outbox backlog queued+claimed={0} while NapCat disconnected" -f ($queued + $claimed))
        [void]$warnings.Add("outbox_backlog_disconnected")
    } elseif (($queued + $claimed) -gt 0) {
        Write-Check warn ("outbox backlog queued+claimed={0} (should drain if NapCat connected)" -f ($queued + $claimed))
        [void]$warnings.Add("outbox_backlog")
    } else {
        Write-Check ok "qq outbox has no queued/claimed backlog"
    }
    if ($summary.pe) {
        Write-Host "  recent private-ecosystem shares:" -ForegroundColor Gray
        foreach ($row in $summary.pe) {
            Write-Host ("    - {0} status={1} mid={2} updated={3}" -f $row.id, $row.status, $row.adapter_message_id, $row.updated_at) -ForegroundColor Gray
        }
    }
}

Write-Host ""
Write-Host ("Summary: fail={0} warn={1}" -f $failures.Count, $warnings.Count)
if ($failures.Count -eq 0) {
    Write-Host "Stack looks ready for QQ delivery." -ForegroundColor Green
} else {
    Write-Host ("Missing: {0}" -f ($failures -join ", ")) -ForegroundColor Red
    Write-Host "Start: .\\XinYu.ps1 start qq" -ForegroundColor Yellow
}

if ($Strict -and $failures.Count -gt 0) {
    exit 1
}
exit 0
