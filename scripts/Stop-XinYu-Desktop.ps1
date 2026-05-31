param(
    [switch]$KeepNapCat,
    [switch]$KeepTinyKernel
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = if (Test-Path -LiteralPath (Join-Path $ScriptDir "XinYu-Core")) {
    $ScriptDir
} else {
    Resolve-Path -LiteralPath (Join-Path $ScriptDir "..")
}
$DesktopDir = Join-Path $Root "XinYu_Desktop"
$NapCatDirCandidates = @(
    (Join-Path $Root "runtime\deps\NapCatQQ\NapCat.44498.Shell"),
    (Join-Path $Root "NapCatQQ\NapCat.44498.Shell")
)
$NapCatDir = $NapCatDirCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $NapCatDir) {
    $NapCatDir = $NapCatDirCandidates[0]
}
$TinyKernelStop = Join-Path $ScriptDir "Stop-XinYu-TinyKernel.ps1"

function Stop-MatchingProcesses {
    param(
        [scriptblock]$Predicate,
        [string]$Label
    )
    $matches = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { & $Predicate $_ } |
        Sort-Object ProcessId -Unique

    foreach ($processInfo in $matches) {
        try {
            Stop-Process -Id ([int]$processInfo.ProcessId) -Force -ErrorAction Stop
            Write-Host "[stop] $Label PID $($processInfo.ProcessId)"
        } catch {
            Write-Host "[warn] Could not stop $Label PID $($processInfo.ProcessId): $($_.Exception.Message)"
        }
    }
}

$desktopPath = [regex]::Escape((Join-Path $DesktopDir "node_modules\electron\dist\electron.exe"))
$desktopDirPattern = [regex]::Escape($DesktopDir)
$napcatDirPattern = if ($NapCatDir) { [regex]::Escape($NapCatDir) } else { "" }

Stop-MatchingProcesses -Label "XinYu Desktop" -Predicate {
    param($p)
    $cmd = [string]$p.CommandLine
    $cmd -match $desktopPath -or $cmd -match $desktopDirPattern -and $cmd -match "electron-vite"
}

Stop-MatchingProcesses -Label "XinYu core/gateway" -Predicate {
    param($p)
    $cmd = [string]$p.CommandLine
    $cmd -match "xinyu_core_bridge\.py" -or $cmd -match "xinyu_qq_gateway\.py"
}

Stop-MatchingProcesses -Label "XinYu startup shell" -Predicate {
    param($p)
    $cmd = [string]$p.CommandLine
    ($cmd -match "Start-XinYu-Desktop\.ps1" -or $cmd -match "Start-XinYu-QQ\.ps1") -and
        $cmd -notmatch "Stop-XinYu-Desktop\.ps1"
}

if (-not $KeepNapCat) {
    Stop-MatchingProcesses -Label "NapCat" -Predicate {
        param($p)
        $cmd = [string]$p.CommandLine
        ($napcatDirPattern -and $cmd -match $napcatDirPattern) -or
            $cmd -match "NapCatWinBootMain\.exe" -or
            $cmd -match "napcat\.bat"
    }
}

if (-not $KeepTinyKernel -and (Test-Path -LiteralPath $TinyKernelStop)) {
    & $TinyKernelStop | Out-Null
}

Write-Host "Done."
