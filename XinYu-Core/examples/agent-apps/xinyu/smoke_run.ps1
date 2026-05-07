param(
    [string]$Message = "你好，心玉。",
    [int]$WarmupSeconds = 2,
    [int]$ReplyWaitSeconds = 20,
    [string]$VenvPath = ".venv"
)

$ErrorActionPreference = "Stop"

$xinyuDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $xinyuDir "$VenvPath\\Scripts\\python.exe"
$launcher = Join-Path $xinyuDir "run_local_xinyu.py"

if (-not (Test-Path $python)) {
    throw "Virtual environment Python not found: $python"
}

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $python
$psi.Arguments = "$launcher --mode plain --no-session"
$psi.UseShellExecute = $false
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.WorkingDirectory = $xinyuDir

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $psi
[void]$process.Start()

Start-Sleep -Seconds $WarmupSeconds
$process.StandardInput.WriteLine($Message)
$process.StandardInput.Flush()

Start-Sleep -Seconds $ReplyWaitSeconds
$process.StandardInput.WriteLine("/exit")
$process.StandardInput.Flush()
$process.StandardInput.Close()

if (-not $process.WaitForExit(120000)) {
    $process.Kill()
}

$stdout = $process.StandardOutput.ReadToEnd()
$stderr = $process.StandardError.ReadToEnd()

Write-Output "=== STDOUT ==="
Write-Output $stdout
Write-Output "=== STDERR ==="
Write-Output $stderr

$latestLog = Get-ChildItem -Path "$HOME\\.xinyu\\logs" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 -ExpandProperty FullName

Write-Output "=== LATEST LOG ==="
Write-Output $latestLog
