param(
    [string]$AstrBotRoot = "D:\XinYu\AstrBot"
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path -LiteralPath $AstrBotRoot).Path
$processes = Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -like "*$root*main.py*" }

if (-not $processes) {
    Write-Host "No AstrBot process found for $root"
    exit 0
}

foreach ($process in $processes) {
    Write-Host "Stopping AstrBot PID=$($process.ProcessId)"
    Stop-Process -Id $process.ProcessId -Force
}
