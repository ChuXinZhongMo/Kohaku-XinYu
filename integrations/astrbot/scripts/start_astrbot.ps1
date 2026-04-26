param(
    [string]$AstrBotRoot = "D:\XinYu\AstrBot"
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path -LiteralPath $AstrBotRoot).Path
$python = Join-Path $root ".venv\Scripts\python.exe"
$main = Join-Path $root "main.py"
$logs = Join-Path $root "logs"
$out = Join-Path $logs "astrbot.out.log"
$err = Join-Path $logs "astrbot.err.log"

if (-not (Test-Path -LiteralPath $python)) {
    throw "AstrBot venv python not found: $python"
}
if (-not (Test-Path -LiteralPath $main)) {
    throw "AstrBot main.py not found: $main"
}

$existing = Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -like "*$root*main.py*" }

if ($existing) {
    $existing | Select-Object ProcessId, CommandLine
    Write-Host "AstrBot already appears to be running."
    exit 0
}

New-Item -ItemType Directory -Force -Path $logs | Out-Null

$command = "set PYTHONIOENCODING=utf-8 && cd /d `"$root`" && `"$python`" main.py > `"$out`" 2> `"$err`""
$process = Start-Process -FilePath $env:ComSpec -ArgumentList "/c", $command -WindowStyle Hidden -PassThru

Write-Host "Started AstrBot launcher PID=$($process.Id)"
Write-Host "WebUI: http://localhost:6185"
Write-Host "Logs: $out / $err"
