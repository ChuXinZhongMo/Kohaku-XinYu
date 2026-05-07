param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 6199
)

$ErrorActionPreference = "Stop"

$listeners = Get-NetTCPConnection -LocalAddress $HostAddress -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $listeners) {
    Write-Host "No XinYu QQ gateway listener found on $HostAddress`:$Port."
    exit 0
}

foreach ($listener in $listeners) {
    $pidValue = [int]$listener.OwningProcess
    $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$pidValue" -ErrorAction SilentlyContinue
    $commandLine = if ($procInfo) { [string]$procInfo.CommandLine } else { "" }

    if ($commandLine -notmatch "xinyu_qq_gateway\.py") {
        Write-Host "Skipping PID $pidValue because it does not look like xinyu_qq_gateway.py."
        Write-Host "CommandLine: $commandLine"
        continue
    }

    Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped XinYu QQ gateway PID $pidValue."
}
