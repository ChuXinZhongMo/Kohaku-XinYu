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
    [string]$SelfCodeSnapshotPath = "",
    [string]$SelfCodeOwnerUserId = "",
    [int]$HealthTimeoutSeconds = 60,
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

function Resolve-SelfCodeSnapshotManifest {
    param([string]$PathText)
    if ([string]::IsNullOrWhiteSpace($PathText)) {
        return ""
    }
    $candidate = if ([System.IO.Path]::IsPathRooted($PathText)) {
        $PathText
    } else {
        Join-Path $xinyuDir $PathText
    }
    $full = [System.IO.Path]::GetFullPath($candidate)
    if (-not (Test-Path -LiteralPath $full)) {
        throw "Self-code snapshot manifest not found: $full"
    }
    return $full
}

function Test-PathUnderRoot {
    param(
        [string]$Candidate,
        [string]$Root
    )
    $candidateFull = [System.IO.Path]::GetFullPath($Candidate).TrimEnd('\')
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd('\')
    return $candidateFull.Equals($rootFull, [System.StringComparison]::OrdinalIgnoreCase) -or
        $candidateFull.StartsWith($rootFull + '\', [System.StringComparison]::OrdinalIgnoreCase)
}

function Get-SelfCodeSnapshotJson {
    param([string]$ManifestPath)
    if ([string]::IsNullOrWhiteSpace($ManifestPath)) {
        return $null
    }
    return Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Write-SelfCodeWatchdogState {
    param(
        [string]$Status,
        [string]$ManifestPath,
        [string]$Reason,
        [string]$Note = ""
    )
    if ([string]::IsNullOrWhiteSpace($ManifestPath)) {
        return
    }
    $manifest = Get-SelfCodeSnapshotJson -ManifestPath $ManifestPath
    if ($null -eq $manifest) {
        return
    }
    $statePath = Join-Path $xinyuDir "memory\context\self_code_watchdog_state.md"
    $stateDir = Split-Path -Parent $statePath
    if (-not (Test-Path -LiteralPath $stateDir)) {
        New-Item -ItemType Directory -Path $stateDir | Out-Null
    }
    $now = Get-Date -Format o
    $snapshotId = [string]$manifest.snapshot_id
    $approvalId = [string]$manifest.approval_id
    $fileCount = @($manifest.files).Count
    $content = @(
        "---",
        "title: Self Code Watchdog State",
        "memory_type: self_code_watchdog_state",
        "time_scope: short_term",
        "subject_ids: [xinyu, owner]",
        "protected: true",
        "source: start_xinyu_core_bridge",
        "updated_at: $now",
        "status: active",
        "tags: [self-code, watchdog, rollback]",
        "---",
        "",
        "# Self Code Watchdog State",
        "",
        "## Latest Snapshot",
        "- observed_at: $now",
        "- status: $Status",
        "- snapshot_id: $snapshotId",
        "- approval_id: $approvalId",
        "- manifest_path: $ManifestPath",
        "- file_count: $fileCount",
        "- reason: $Reason",
        "",
        "## Rules",
        "- health_gate_owner: start_xinyu_core_bridge.ps1",
        "- rollback_scope: existing XinYu app code and startup files captured in the snapshot",
        "- stable_memory_write: blocked",
        "",
        "## Notes",
        "- $Note"
    ) -join "`n"
    Set-Content -LiteralPath $statePath -Value ($content + "`n") -Encoding UTF8
}

function Get-OwnerUserId {
    if (-not [string]::IsNullOrWhiteSpace($SelfCodeOwnerUserId)) {
        return $SelfCodeOwnerUserId.Trim()
    }
    $configPath = Join-Path $xinyuDir "xinyu_qq_gateway.config.json"
    if (-not (Test-Path -LiteralPath $configPath)) {
        return ""
    }
    try {
        $config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $owners = @($config.owner_user_ids)
        if ($owners.Count -gt 0) {
            return [string]$owners[0]
        }
    } catch {
        return ""
    }
    return ""
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

function Stop-BridgeProcessFamily {
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

function Add-OwnerOutboxMessage {
    param(
        [string]$Message,
        [string]$DedupeKey
    )
    $ownerId = Get-OwnerUserId
    if ([string]::IsNullOrWhiteSpace($ownerId) -or [string]::IsNullOrWhiteSpace($Message)) {
        return
    }
    $queuePath = Join-Path $xinyuDir "memory\context\qq_outbox_queue.json"
    $queueDir = Split-Path -Parent $queuePath
    if (-not (Test-Path -LiteralPath $queueDir)) {
        New-Item -ItemType Directory -Path $queueDir | Out-Null
    }
    $now = Get-Date -Format o
    $data = $null
    if (Test-Path -LiteralPath $queuePath) {
        try {
            $data = Get-Content -LiteralPath $queuePath -Raw -Encoding UTF8 | ConvertFrom-Json
        } catch {
            $data = $null
        }
    }
    if ($null -eq $data) {
        $data = [pscustomobject]@{ version = 1; updated_at = $now; items = @() }
    }
    $items = @($data.items)
    foreach ($item in $items) {
        if ([string]$item.dedupe_key -eq $DedupeKey -and @("queued", "claimed", "sent") -contains [string]$item.status) {
            return
        }
    }
    $idStamp = Get-Date -Format "yyyyMMddTHHmmss"
    $messageId = "self-code-watchdog-$idStamp"
    $newItem = [ordered]@{
        id = $messageId
        status = "queued"
        created_at = $now
        updated_at = $now
        source = "self_code_watchdog"
        dedupe_key = $DedupeKey
        target = [ordered]@{ message_kind = "private"; user_id = $ownerId; group_id = "" }
        message = $Message
        attempts = 0
        claim_id = ""
        claimed_at = ""
        acked_at = ""
        adapter = ""
        adapter_message_id = ""
        adapter_error = ""
        metadata = [ordered]@{ watchdog = $true }
    }
    $data = [ordered]@{
        version = 1
        updated_at = $now
        items = @($items + [pscustomobject]$newItem)
    }
    $tmp = Join-Path $queueDir (".qq_outbox_queue." + [System.Guid]::NewGuid().ToString("N") + ".tmp")
    $data | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $tmp -Encoding UTF8
    Move-Item -LiteralPath $tmp -Destination $queuePath -Force
}

function Restore-SelfCodeSnapshot {
    param([string]$ManifestPath)
    $manifest = Get-SelfCodeSnapshotJson -ManifestPath $ManifestPath
    if ($null -eq $manifest) {
        throw "Could not read self-code snapshot manifest: $ManifestPath"
    }
    $manifestRoot = [System.IO.Path]::GetFullPath([string]$manifest.root).TrimEnd('\')
    $currentRoot = [System.IO.Path]::GetFullPath($xinyuDir).TrimEnd('\')
    if (-not $manifestRoot.Equals($currentRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Snapshot root mismatch. manifest=$manifestRoot current=$currentRoot"
    }

    $restored = 0
    foreach ($file in @($manifest.files)) {
        $rel = ([string]$file.rel_path).Replace('/', '\')
        if ([string]::IsNullOrWhiteSpace($rel) -or $rel.Contains("..")) {
            continue
        }
        $target = [System.IO.Path]::GetFullPath((Join-Path $xinyuDir $rel))
        if (-not (Test-PathUnderRoot -Candidate $target -Root $xinyuDir)) {
            continue
        }
        $backup = [System.IO.Path]::GetFullPath([string]$file.backup_path)
        if (-not (Test-Path -LiteralPath $backup)) {
            continue
        }
        $targetDir = Split-Path -Parent $target
        if (-not (Test-Path -LiteralPath $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir | Out-Null
        }
        Copy-Item -LiteralPath $backup -Destination $target -Force
        $restored += 1
    }
    Write-SelfCodeWatchdogState -Status "restored" -ManifestPath $ManifestPath -Reason "startup_health_failed" -Note "restored_files:$restored"
    return $restored
}

function Wait-CoreBridgeHealth {
    param(
        [System.Diagnostics.Process]$Process,
        [int]$TimeoutSeconds
    )
    $deadline = (Get-Date).AddSeconds([Math]::Max(1, $TimeoutSeconds))
    while ((Get-Date) -lt $deadline) {
        $health = Get-RunningBridgeHealth
        if ($health -and $health.ok) {
            return $health
        }
        Start-Sleep -Milliseconds 1000
    }
    return $null
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

$snapshotManifest = Resolve-SelfCodeSnapshotManifest -PathText $SelfCodeSnapshotPath
$sourceVersion = Get-SourceBridgeVersion
$listener = Get-NetTCPConnection -LocalAddress $HostAddress -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $pidValue = [int]$listener.OwningProcess
    $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$pidValue" -ErrorAction SilentlyContinue
    $commandLine = if ($procInfo) { [string]$procInfo.CommandLine } else { "" }
    if ($commandLine -match "xinyu_core_bridge\.py") {
        if ($ForceRestart) {
            Write-Host "Stopping XinYu core bridge PID $pidValue for forced restart."
            Stop-BridgeProcessFamily -ListenerPid $pidValue -ScriptPattern "xinyu_core_bridge\.py"
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

$effectiveBridgeToken = Resolve-BridgeToken
$bridgeArgs = @(
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
if ($effectiveBridgeToken) {
    $bridgeArgs += @("--bridge-token", $effectiveBridgeToken)
}

if ($AllowInsecureLlmHttp) {
    $env:XINYU_ALLOW_INSECURE_LLM_HTTP = "1"
}

function Start-CoreBridgeProcess {
    return Start-Process `
        -FilePath $venvPython `
        -ArgumentList $script:bridgeArgs `
        -WorkingDirectory $xinyuDir `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -WindowStyle Hidden `
        -PassThru
}

function Stop-CoreBridgeProcess {
    param([System.Diagnostics.Process]$Process)
    if ($Process -and -not $Process.HasExited) {
        try {
            Stop-Process -Id $Process.Id -Force
            Start-Sleep -Seconds 1
        } catch {
        }
    }
}

$process = Start-CoreBridgeProcess
$health = Wait-CoreBridgeHealth -Process $process -TimeoutSeconds $HealthTimeoutSeconds
$healthOk = $false
if ($health) {
    $healthOk = $true
    if ($RequireVersion -and [string]$health.version -ne $sourceVersion) {
        $healthOk = $false
        Write-Host "Started bridge version mismatch: running=$($health.version) source=$sourceVersion"
    }
}

if ($healthOk) {
    $listener = Get-NetTCPConnection -LocalAddress $HostAddress -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    $listenerPid = if ($listener) { $listener.OwningProcess } else { "unknown" }
    $auto = $health.autonomous_maintenance
    Write-Host "XinYu core bridge started. launcher PID: $($process.Id), listener PID: $listenerPid"
    Write-Host "Health: ok=$($health.ok), sessions=$($health.sessions), autonomous=$($auto.enabled)/task=$($auto.task_running), url=http://$HostAddress`:$Port/chat"
    Write-Host "Logs: $stdoutLog"
    if ($snapshotManifest) {
        Write-SelfCodeWatchdogState -Status "health_passed" -ManifestPath $snapshotManifest -Reason "startup_health_ok" -Note "rollback_not_needed"
        Add-OwnerOutboxMessage -DedupeKey "self-code-watchdog-success:$snapshotManifest" -Message "Self-code hot reload passed the 30s health gate. Core is running normally."
    }
    exit 0
}

Write-Host "XinYu core bridge process started but health check failed. PID: $($process.Id)"
Write-Host "Check logs: $stdoutLog"
Write-Host "Errors: $stderrLog"

if (-not $snapshotManifest) {
    Stop-CoreBridgeProcess -Process $process
    throw "XinYu core bridge failed health check after startup."
}

Write-Host "Self-code snapshot provided. Rolling back before restart: $snapshotManifest"
Stop-CoreBridgeProcess -Process $process
$restoredCount = Restore-SelfCodeSnapshot -ManifestPath $snapshotManifest
Write-Host "Restored $restoredCount file(s) from self-code snapshot."

$rollbackProcess = Start-CoreBridgeProcess
$rollbackHealth = Wait-CoreBridgeHealth -Process $rollbackProcess -TimeoutSeconds $HealthTimeoutSeconds
if ($rollbackHealth -and (-not $RequireVersion -or [string]$rollbackHealth.version -eq $sourceVersion)) {
    $listener = Get-NetTCPConnection -LocalAddress $HostAddress -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    $listenerPid = if ($listener) { $listener.OwningProcess } else { "unknown" }
    $auto = $rollbackHealth.autonomous_maintenance
    Write-SelfCodeWatchdogState -Status "rolled_back_and_running" -ManifestPath $snapshotManifest -Reason "startup_health_failed_then_restored" -Note "restored_files:$restoredCount"
    Add-OwnerOutboxMessage -DedupeKey "self-code-watchdog-rollback:$snapshotManifest" -Message "Self-code patch failed the startup health gate. I restored the previous snapshot and Core is running again."
    Write-Host "XinYu core bridge rolled back and restarted. launcher PID: $($rollbackProcess.Id), listener PID: $listenerPid"
    Write-Host "Health: ok=$($rollbackHealth.ok), sessions=$($rollbackHealth.sessions), autonomous=$($auto.enabled)/task=$($auto.task_running), url=http://$HostAddress`:$Port/chat"
    Write-Host "Logs: $stdoutLog"
    exit 0
}

Stop-CoreBridgeProcess -Process $rollbackProcess
Write-SelfCodeWatchdogState -Status "rollback_failed" -ManifestPath $snapshotManifest -Reason "restored_startup_health_failed" -Note "manual_intervention_required"
Add-OwnerOutboxMessage -DedupeKey "self-code-watchdog-rollback-failed:$snapshotManifest" -Message "Emergency: self-code patch failed and rollback restart also failed. Manual terminal intervention is required."
throw "XinYu core bridge failed health check after rollback restart."
