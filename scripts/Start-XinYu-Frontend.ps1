param(
    [switch]$Prod,
    [switch]$Build,
    [switch]$ForceRestart,
    [switch]$SkipCoreBridge
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
$CoreDir = Join-Path $Root "XinYu-Core\examples\agent-apps\xinyu"
$CoreStart = Join-Path $CoreDir "start_xinyu_core_bridge.ps1"
$BridgeTokenPath = Join-Path $Root ".xinyu_bridge_token"
$ElectronExe = Join-Path $DesktopDir "node_modules\electron\dist\electron.exe"
$BuiltMain = Join-Path $DesktopDir "out\main\index.js"
$LogDir = Join-Path $DesktopDir "logs"
$DevOutLog = Join-Path $LogDir "frontend-dev.out.log"
$DevErrLog = Join-Path $LogDir "frontend-dev.err.log"

function Get-FrontendDevProcesses {
    $desktopPattern = [regex]::Escape($DesktopDir)
    return Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $commandLine = [string]$_.CommandLine
            $commandLine -match $desktopPattern -and $commandLine -match "electron-vite" -and $commandLine -match "\bdev\b"
        }
}

function Test-FrontendDevRunning {
    return $null -ne (Get-FrontendDevProcesses | Select-Object -First 1)
}

function Test-FrontendProdRunning {
    if (-not (Test-Path -LiteralPath $ElectronExe)) {
        return $false
    }
    $electronPattern = [regex]::Escape($ElectronExe)
    $process = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $commandLine = [string]$_.CommandLine
            $commandLine -match $electronPattern -and
                $commandLine -notmatch "\s--type=" -and
                $commandLine -match "\s\."
        } |
        Select-Object -First 1
    return $null -ne $process
}

function Get-FrontendRootProcesses {
    $desktopPattern = [regex]::Escape($DesktopDir)
    $electronPattern = [regex]::Escape($ElectronExe)
    return Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $commandLine = [string]$_.CommandLine
            (
                $commandLine -match $desktopPattern -and
                $commandLine -match "electron-vite" -and
                $commandLine -match "\bdev\b"
            ) -or (
                $commandLine -match $electronPattern -and
                $commandLine -notmatch "\s--type=" -and
                $commandLine -match "\s\."
            )
        } |
        Sort-Object ProcessId -Unique
}

function Stop-FrontendProcesses {
    foreach ($processInfo in (Get-FrontendRootProcesses)) {
        try {
            Stop-Process -Id ([int]$processInfo.ProcessId) -Force -ErrorAction Stop
            Write-Host "[restart] stopped stale XinYu frontend PID $($processInfo.ProcessId)"
        } catch {
            Write-Host "[warn] could not stop XinYu frontend PID $($processInfo.ProcessId): $($_.Exception.Message)"
        }
    }
    Start-Sleep -Seconds 1
}

function Get-LatestNativeFrontendWriteTime {
    $paths = @(
        (Join-Path $DesktopDir "src\main"),
        (Join-Path $DesktopDir "src\preload"),
        (Join-Path $DesktopDir "electron.vite.config.ts"),
        (Join-Path $DesktopDir "package.json")
    )
    $latest = $null
    foreach ($path in $paths) {
        if (-not (Test-Path -LiteralPath $path)) {
            continue
        }
        $items = if ((Get-Item -LiteralPath $path).PSIsContainer) {
            Get-ChildItem -LiteralPath $path -Recurse -File -ErrorAction SilentlyContinue
        } else {
            @(Get-Item -LiteralPath $path)
        }
        foreach ($item in $items) {
            if ($null -eq $latest -or $item.LastWriteTime -gt $latest) {
                $latest = $item.LastWriteTime
            }
        }
    }
    return $latest
}

function Test-FrontendNativeCodeNewerThanProcess {
    $latestWrite = Get-LatestNativeFrontendWriteTime
    if ($null -eq $latestWrite) {
        return $false
    }
    $oldestStart = $null
    foreach ($processInfo in (Get-FrontendRootProcesses)) {
        $startedAt = if ($processInfo.CreationDate -is [datetime]) {
            $processInfo.CreationDate
        } else {
            [Management.ManagementDateTimeConverter]::ToDateTime([string]$processInfo.CreationDate)
        }
        if ($null -eq $oldestStart -or $startedAt -lt $oldestStart) {
            $oldestStart = $startedAt
        }
    }
    return $null -ne $oldestStart -and $latestWrite -gt $oldestStart
}

function Require-Npm {
    if (-not (Get-Command "npm.cmd" -ErrorAction SilentlyContinue)) {
        throw "npm.cmd was not found in PATH. Install Node.js first, then run this launcher again."
    }
}

function Ensure-Dependencies {
    $viteBin = Join-Path $DesktopDir "node_modules\.bin\electron-vite.cmd"
    if (Test-Path -LiteralPath $viteBin) {
        return
    }
    Write-Host "[deps] node_modules is missing or incomplete; running npm install..."
    Push-Location $DesktopDir
    try {
        & npm.cmd install
    } finally {
        Pop-Location
    }
}

function Import-BridgeToken {
    $env:XINYU_ROOT = $Root
    if ($env:XINYU_BRIDGE_TOKEN) {
        return
    }
    if (Test-Path -LiteralPath $BridgeTokenPath) {
        $token = (Get-Content -LiteralPath $BridgeTokenPath -Raw -Encoding ASCII).Trim()
        if ($token) {
            $env:XINYU_BRIDGE_TOKEN = $token
        }
    }
}

function Ensure-CoreBridge {
    if ($SkipCoreBridge) {
        return
    }
    if (-not (Test-Path -LiteralPath $CoreStart)) {
        Write-Host "[warn] XinYu core bridge start script not found: $CoreStart"
        return
    }

    $sourceVersion = ""
    try {
        $bridgeSource = Get-Content -LiteralPath (Join-Path $CoreDir "xinyu_core_bridge.py") -Raw -Encoding UTF8
        $match = [regex]::Match($bridgeSource, 'BRIDGE_VERSION\s*=\s*["'']([^"'']+)["'']')
        if ($match.Success) {
            $sourceVersion = $match.Groups[1].Value
        }
    } catch {
        $sourceVersion = ""
    }

    $health = $null
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8765/health" -Method Get -TimeoutSec 5
    } catch {
        $health = $null
    }
    $restart = [bool]$ForceRestart
    if ($health -and $health.ok -and $sourceVersion -and [string]$health.version -ne $sourceVersion) {
        Write-Host "[restart] XinYu core bridge version drift: running=$($health.version) source=$sourceVersion"
        $restart = $true
    } elseif ($health -and $health.ok -and -not $restart) {
        Write-Host "[ok] XinYu core bridge already running: http://127.0.0.1:8765"
        return
    }

    $coreArgs = @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $CoreStart,
        "-Port",
        "8765",
        "-AllowInsecureLlmHttp"
    )
    if ($restart) {
        $coreArgs += "-ForceRestart"
    }
    $process = Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList $coreArgs `
        -WorkingDirectory $CoreDir `
        -WindowStyle Hidden `
        -Wait `
        -PassThru
    if ($process.ExitCode -ne 0) {
        throw "XinYu core bridge start script failed with exit code $($process.ExitCode). Check logs under $CoreDir\logs."
    }
}

if (-not (Test-Path -LiteralPath $DesktopDir)) {
    throw "XinYu frontend directory not found: $DesktopDir"
}

Require-Npm
Ensure-Dependencies
Import-BridgeToken
Ensure-CoreBridge

if ($Prod) {
    if ((-not (Test-Path -LiteralPath $BuiltMain)) -or $Build) {
        Push-Location $DesktopDir
        try {
            & npm.cmd run build
        } finally {
            Pop-Location
        }
    }
    if (-not (Test-Path -LiteralPath $ElectronExe)) {
        throw "Electron executable not found: $ElectronExe"
    }
    if ($ForceRestart) {
        Stop-FrontendProcesses
    }
    if (Test-FrontendProdRunning) {
        Write-Host "[ok] XinYu frontend is already running in production mode."
        return
    }
    Start-Process -FilePath $ElectronExe -ArgumentList "." -WorkingDirectory $DesktopDir
    Write-Host "[start] XinYu frontend production window opened."
    return
}

if ($ForceRestart) {
    Stop-FrontendProcesses
} elseif (Test-FrontendDevRunning -and (Test-FrontendNativeCodeNewerThanProcess)) {
    Stop-FrontendProcesses
}

if (Test-FrontendDevRunning) {
    Write-Host "[ok] XinYu frontend dev server is already running."
    return
}

if (-not (Test-Path -LiteralPath $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}
Start-Process `
    -FilePath "cmd.exe" `
    -ArgumentList @("/c", "npm.cmd run dev") `
    -WorkingDirectory $DesktopDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $DevOutLog `
    -RedirectStandardError $DevErrLog
Write-Host "[start] XinYu frontend dev server started in the background."
Write-Host "[log] $DevOutLog"
