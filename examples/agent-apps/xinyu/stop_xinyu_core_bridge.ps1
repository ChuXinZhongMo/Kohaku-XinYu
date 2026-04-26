param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

$listeners = Get-NetTCPConnection -LocalAddress $HostAddress -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $listeners) {
    Write-Host "No listener found on $HostAddress`:$Port."
    exit 0
}

foreach ($listener in $listeners) {
    $pidValue = [int]$listener.OwningProcess
    $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$pidValue" -ErrorAction SilentlyContinue
    $commandLine = if ($procInfo) { [string]$procInfo.CommandLine } else { "" }

    if ($commandLine -notmatch "xinyu_core_bridge\.py") {
        Write-Host "Skipping PID $pidValue because it does not look like xinyu_core_bridge.py."
        Write-Host "CommandLine: $commandLine"
        continue
    }

    $bridgeProcesses = Get-CimInstance Win32_Process | Where-Object {
        [string]$_.CommandLine -match "xinyu_core_bridge\.py"
    }

    $targetIds = New-Object System.Collections.Generic.HashSet[int]
    [void]$targetIds.Add($pidValue)

    if ($procInfo -and $procInfo.ParentProcessId) {
        $parent = $bridgeProcesses | Where-Object { $_.ProcessId -eq $procInfo.ParentProcessId } | Select-Object -First 1
        if ($parent) {
            [void]$targetIds.Add([int]$parent.ProcessId)
        }
    }

    $children = $bridgeProcesses | Where-Object { $_.ParentProcessId -eq $pidValue }
    foreach ($child in $children) {
        [void]$targetIds.Add([int]$child.ProcessId)
    }

    foreach ($targetId in $targetIds) {
        Stop-Process -Id $targetId -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped XinYu core bridge PID $targetId."
    }
}
