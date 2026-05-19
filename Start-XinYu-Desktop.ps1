param(
    [switch]$Build,
    [switch]$Dev,
    [switch]$ShowConsoles,
    [switch]$OpenNapCatWebUI,
    [switch]$SkipTinyKernel
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DesktopDir = Join-Path $Root "XinYu_Desktop"
$QQStart = Join-Path $Root "Start-XinYu-QQ.ps1"
$TinyKernelStart = Join-Path $Root "Start-XinYu-TinyKernel.ps1"
$ElectronExe = Join-Path $DesktopDir "node_modules\electron\dist\electron.exe"
$BuiltMain = Join-Path $DesktopDir "out\main\index.js"

function Test-ProcessCommandLine {
    param([string]$Pattern)
    $escaped = [regex]::Escape($Pattern)
    $process = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { [string]$_.CommandLine -match $escaped } |
        Select-Object -First 1
    return $null -ne $process
}

function Test-DesktopRunning {
    $electronPath = [regex]::Escape($ElectronExe)
    $process = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $commandLine = [string]$_.CommandLine
            $commandLine -match $electronPath -and
                $commandLine -notmatch "\s--type=" -and
                $commandLine -match "\s\."
        } |
        Select-Object -First 1
    return $null -ne $process
}

function Start-QQRuntime {
    if (-not (Test-Path -LiteralPath $QQStart)) {
        throw "QQ startup script not found: $QQStart"
    }

    $napcatStyle = if ($ShowConsoles) { "Normal" } else { "Hidden" }
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $QQStart,
        "-NapCatConsoleWindowStyle",
        $napcatStyle
    )
    if ($OpenNapCatWebUI) {
        $args += "-OpenDashboards"
    }

    if ($ShowConsoles) {
        Start-Process -FilePath "powershell.exe" -ArgumentList (@("-NoExit") + $args) -WorkingDirectory $Root -WindowStyle Normal
    } else {
        Start-Process -FilePath "powershell.exe" -ArgumentList $args -WorkingDirectory $Root -WindowStyle Hidden
    }
}

function Start-TinyKernelRuntime {
    if ($SkipTinyKernel) {
        return
    }
    if (-not (Test-Path -LiteralPath $TinyKernelStart)) {
        return
    }
    & $TinyKernelStart | Out-Null
}

function Ensure-DesktopBuild {
    if ($Dev) {
        return
    }
    if ((-not $Build) -and (Test-Path -LiteralPath $BuiltMain)) {
        return
    }
    if (-not (Get-Command "npm.cmd" -ErrorAction SilentlyContinue)) {
        throw "npm.cmd was not found in PATH. Build XinYu_Desktop once from a terminal."
    }
    Push-Location $DesktopDir
    try {
        & npm.cmd run build
    } finally {
        Pop-Location
    }
}

function Start-Desktop {
    if (-not (Test-Path -LiteralPath $DesktopDir)) {
        throw "Desktop directory not found: $DesktopDir"
    }

    if ($Dev) {
        if (Test-ProcessCommandLine "electron-vite dev") {
            return
        }
        $devArgs = @("-NoProfile", "-Command", "npm run dev")
        $windowStyle = if ($ShowConsoles) { "Normal" } else { "Hidden" }
        Start-Process -FilePath "powershell.exe" -ArgumentList $devArgs -WorkingDirectory $DesktopDir -WindowStyle $windowStyle
        return
    }

    if (-not (Test-Path -LiteralPath $ElectronExe)) {
        throw "Electron executable not found: $ElectronExe"
    }
    if (-not (Test-Path -LiteralPath $BuiltMain)) {
        throw "Built desktop entry not found: $BuiltMain"
    }
    if (Test-DesktopRunning) {
        return
    }
    Start-Process -FilePath $ElectronExe -ArgumentList "." -WorkingDirectory $DesktopDir
}

Start-TinyKernelRuntime
Start-QQRuntime
Ensure-DesktopBuild
Start-Desktop
