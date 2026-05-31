param(
    [switch]$Prod,
    [switch]$Build
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
$BridgeTokenPath = Join-Path $Root ".xinyu_bridge_token"
$ElectronExe = Join-Path $DesktopDir "node_modules\electron\dist\electron.exe"
$BuiltMain = Join-Path $DesktopDir "out\main\index.js"
$LogDir = Join-Path $DesktopDir "logs"
$DevOutLog = Join-Path $LogDir "frontend-dev.out.log"
$DevErrLog = Join-Path $LogDir "frontend-dev.err.log"

function Test-FrontendDevRunning {
    $desktopPattern = [regex]::Escape($DesktopDir)
    $process = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $commandLine = [string]$_.CommandLine
            $commandLine -match $desktopPattern -and $commandLine -match "electron-vite" -and $commandLine -match "\bdev\b"
        } |
        Select-Object -First 1
    return $null -ne $process
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

if (-not (Test-Path -LiteralPath $DesktopDir)) {
    throw "XinYu frontend directory not found: $DesktopDir"
}

Require-Npm
Ensure-Dependencies
Import-BridgeToken

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
    if (Test-FrontendProdRunning) {
        Write-Host "[ok] XinYu frontend is already running in production mode."
        return
    }
    Start-Process -FilePath $ElectronExe -ArgumentList "." -WorkingDirectory $DesktopDir
    Write-Host "[start] XinYu frontend production window opened."
    return
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
