param(
    [switch]$KeepNapCat
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DesktopDir = Join-Path $Root "XinYu_Desktop"
$NapCatDir = Join-Path $Root "NapCatQQ\NapCat.44498.Shell"

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
$napcatDirPattern = [regex]::Escape($NapCatDir)

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
        $cmd -match $napcatDirPattern -or
            $cmd -match "NapCatWinBootMain\.exe" -or
            $cmd -match "napcat\.bat"
    }
}

Write-Host "Done."
