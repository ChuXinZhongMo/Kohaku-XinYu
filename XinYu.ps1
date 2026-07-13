param(
    [Parameter(Position = 0)]
    [ValidateSet("tree", "status", "start", "stop", "test", "smoke", "verify", "clean", "health")]
    [string]$Command = "tree",

    [Parameter(Position = 1)]
    [ValidateSet("all", "desktop", "qq", "tinykernel", "core")]
    [string]$Target = "all",

    [switch]$Dev,
    [switch]$Build,
    [switch]$ShowConsoles,
    [switch]$OpenDashboards,
    [switch]$SkipTinyKernel,
    [int]$KeepRuntimeRuns = 8,
    [int]$MinRuntimeAgeMinutes = 10
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$CoreRoot = Join-Path $Root "XinYu-Core"
$AppRoot = Join-Path $CoreRoot "examples\agent-apps\xinyu"
$DesktopRoot = Join-Path $Root "XinYu_Desktop"
$TinyKernelRoot = Join-Path $Root "XinYu-TinyKernel"
$LocalScopeRoot = Join-Path $Root "XinYu-Local-Scope"
$AutonomyRoot = Join-Path $Root "XinYu-Autonomy"
$RuntimeRoot = Join-Path $AppRoot "runtime"
$ScriptsRoot = Join-Path $Root "scripts"
$DocsRoot = Join-Path $Root "docs"
$AssetsRoot = Join-Path $Root "assets"
$ArtifactsRoot = Join-Path $Root "artifacts"

function Resolve-XinYuScript {
    param([string]$Name)
    $candidates = @(
        (Join-Path $ScriptsRoot $Name),
        (Join-Path $Root $Name)
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    return $candidates[0]
}

function Resolve-XinYuPython {
    $candidates = @(
        (Join-Path $AppRoot ".venv\Scripts\python.exe"),
        (Join-Path $Root "runtime\deps\Python312\python.exe"),
        (Join-Path $Root "Python312\python.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    $cmd = Get-Command "python" -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    throw "No Python interpreter found for XinYu."
}

function Write-ComponentTree {
    $components = @(
        @{ Name = "core"; Path = $CoreRoot; Role = "Python runtime framework and app host" },
        @{ Name = "app"; Path = $AppRoot; Role = "active XinYu bridge, QQ gateway, memory/runtime boundary" },
        @{ Name = "desktop"; Path = $DesktopRoot; Role = "Electron desktop shell" },
        @{ Name = "tinykernel"; Path = $TinyKernelRoot; Role = "local tiny-kernel service and experiments" },
        @{ Name = "local-scope"; Path = $LocalScopeRoot; Role = "owner-controlled local request/material area" },
        @{ Name = "autonomy"; Path = $AutonomyRoot; Role = "owner-visible autonomy notes" },
        @{ Name = "docs"; Path = $DocsRoot; Role = "system notes, plans, reports, and runbooks" },
        @{ Name = "assets"; Path = $AssetsRoot; Role = "cases, reference library, icons, OCR fixtures, and materials" },
        @{ Name = "artifacts"; Path = $ArtifactsRoot; Role = "archives, generated packages, and protection snapshots" },
        @{ Name = "scripts"; Path = $ScriptsRoot; Role = "startup, shutdown, and local operator helpers" },
        @{ Name = "deps"; Path = (Join-Path $Root "runtime\deps"); Role = "local Python, OCR, vision, and adapter runtimes" },
        @{ Name = "napcat"; Path = (Join-Path $Root "runtime\deps\NapCatQQ"); Role = "external QQ adapter runtime" }
    )

    Write-Host "XinYu system root: $Root"
    Write-Host ""
    foreach ($component in $components) {
        $exists = if (Test-Path -LiteralPath $component.Path) { "ok" } else { "missing" }
        Write-Host ("[{0}] {1,-12} {2}" -f $exists, $component.Name, $component.Path)
        Write-Host ("     {0}" -f $component.Role)
    }
    Write-Host ""
    Write-Host "Common commands:"
    Write-Host "  .\XinYu.ps1 status"
    Write-Host "  .\XinYu.ps1 health"
    Write-Host "  .\XinYu.ps1 start desktop"
    Write-Host "  .\XinYu.ps1 start qq"
    Write-Host "  .\XinYu.ps1 stop all"
    Write-Host "  .\XinYu.ps1 test core"
    Write-Host "  .\XinYu.ps1 verify qq"
    Write-Host "  .\Verify-XinYu-QQ.cmd"
    Write-Host "  .\XinYu.ps1 clean"
}

function Invoke-CoreStatus {
    $python = Resolve-XinYuPython
    Push-Location $AppRoot
    try {
        & $python "xinyu_status.py" "--json"
    } finally {
        Pop-Location
    }
}

function Invoke-CoreTests {
    $python = Resolve-XinYuPython
    Push-Location $AppRoot
    try {
        & $python "-m" "pytest" "tests" "-q"
    } finally {
        Pop-Location
    }
}

function Invoke-CoreSmoke {
    $python = Resolve-XinYuPython
    Push-Location $AppRoot
    try {
        & $python "smoke_run.py" "--group" "quick" "--timeout-seconds" "180" "--json"
    } finally {
        Pop-Location
    }
}

function Invoke-XinYuVerifyStep {
    param(
        [string]$Python,
        [string]$ScriptName,
        [string[]]$ExtraArgs = @()
    )
    & $Python $ScriptName "--root" $AppRoot @ExtraArgs
    if ($LASTEXITCODE -ne 0) {
        throw "$ScriptName failed with exit code $LASTEXITCODE"
    }
}

function Invoke-XinYuVerify {
    $python = Resolve-XinYuPython
    switch ($Target) {
        "all" {
            Push-Location $AppRoot
            try {
                Invoke-XinYuVerifyStep -Python $python -ScriptName "xinyu_private_reply_selftest.py"
                Write-Host ""
                Invoke-XinYuVerifyStep -Python $python -ScriptName "xinyu_live_loop_report.py" -ExtraArgs @("--wait-seconds", "90")
            } finally {
                Pop-Location
            }
        }
        "qq" {
            Push-Location $AppRoot
            try {
                Invoke-XinYuVerifyStep -Python $python -ScriptName "xinyu_private_reply_selftest.py"
                Write-Host ""
                Invoke-XinYuVerifyStep -Python $python -ScriptName "xinyu_live_loop_report.py" -ExtraArgs @("--wait-seconds", "90")
            } finally {
                Pop-Location
            }
        }
        default {
            throw "Verify target '$Target' is not supported. Use: .\XinYu.ps1 verify qq"
        }
    }
}

function Start-XinYuTarget {
    switch ($Target) {
        "all" {
            $params = @{}
            if ($Dev) { $params.Dev = $true }
            if ($Build) { $params.Build = $true }
            if ($ShowConsoles) { $params.ShowConsoles = $true }
            if ($OpenDashboards) { $params.OpenNapCatWebUI = $true }
            if ($SkipTinyKernel) { $params.SkipTinyKernel = $true }
            & (Resolve-XinYuScript "Start-XinYu-Desktop.ps1") @params
        }
        "desktop" {
            $params = @{ SkipTinyKernel = $true }
            if ($Dev) { $params.Dev = $true }
            if ($Build) { $params.Build = $true }
            if ($ShowConsoles) { $params.ShowConsoles = $true }
            & (Resolve-XinYuScript "Start-XinYu-Desktop.ps1") @params
        }
        "qq" {
            $params = @{
                NapCatConsoleWindowStyle = if ($ShowConsoles) { "Normal" } else { "Hidden" }
            }
            if ($OpenDashboards) { $params.OpenDashboards = $true }
            & (Resolve-XinYuScript "Start-XinYu-QQ.ps1") @params
        }
        "tinykernel" {
            & (Resolve-XinYuScript "Start-XinYu-TinyKernel.ps1")
        }
        "core" {
            Push-Location $AppRoot
            try {
                & ".\start_xinyu_core_bridge.ps1" -AllowInsecureLlmHttp
            } finally {
                Pop-Location
            }
        }
    }
}

function Stop-XinYuTarget {
    switch ($Target) {
        "all" { & (Resolve-XinYuScript "Stop-XinYu-Desktop.ps1") }
        "desktop" { & (Resolve-XinYuScript "Stop-XinYu-Desktop.ps1") -KeepNapCat -KeepTinyKernel }
        "qq" {
            Push-Location $AppRoot
            try {
                & ".\stop_xinyu_qq_gateway.ps1"
                & ".\stop_xinyu_core_bridge.ps1"
            } finally {
                Pop-Location
            }
        }
        "tinykernel" { & (Resolve-XinYuScript "Stop-XinYu-TinyKernel.ps1") }
        "core" {
            Push-Location $AppRoot
            try {
                & ".\stop_xinyu_core_bridge.ps1"
            } finally {
                Pop-Location
            }
        }
    }
}

function Remove-OldRunDirectories {
    param(
        [string]$Parent,
        [string[]]$Prefixes
    )
    if (-not (Test-Path -LiteralPath $Parent)) {
        return
    }
    $now = Get-Date
    $runs = @()
    foreach ($child in Get-ChildItem -Force -LiteralPath $Parent -Directory -ErrorAction SilentlyContinue) {
        $matchesPrefix = $false
        foreach ($prefix in $Prefixes) {
            if ($child.Name.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
                $matchesPrefix = $true
                break
            }
        }
        if (-not $matchesPrefix) {
            continue
        }
        $runs += $child
    }
    $runs = $runs | Sort-Object LastWriteTime -Descending
    for ($i = 0; $i -lt $runs.Count; $i++) {
        $age = $now - $runs[$i].LastWriteTime
        if ($i -lt $KeepRuntimeRuns -or $age.TotalMinutes -lt $MinRuntimeAgeMinutes) {
            continue
        }
        Remove-Item -LiteralPath $runs[$i].FullName -Recurse -Force
        Write-Host "[clean] $($runs[$i].FullName)"
    }
}

function Invoke-XinYuClean {
    if (-not (Test-Path -LiteralPath $RuntimeRoot)) {
        Write-Host "No app runtime directory found: $RuntimeRoot"
    } else {
        Remove-OldRunDirectories -Parent $RuntimeRoot -Prefixes @(
            "pytest-tmp",
            "pytest_tmp",
            "codex_pytest_tmp",
            "codex-pytest",
            "codex_tmp",
            "debug-",
            "tmp-",
            "action_layer_smoke_tmp",
            "action_experience_digest_smoke_tmp",
            "recent_attachment_context_smoke_tmp"
        )

        $pytestTmp = Join-Path $RuntimeRoot "pytest-tmp"
        if (Test-Path -LiteralPath $pytestTmp) {
            Remove-OldRunDirectories -Parent $pytestTmp -Prefixes @("run-")
        }
    }

    $skip = @(".git", ".venv", ".venv-train", "node_modules", "Python312", "ocr-venv", "vision-venv", "NapCatQQ")
    $depsRoot = Join-Path $Root "runtime\deps"
    $stack = [System.Collections.Generic.Stack[string]]::new()
    $stack.Push($Root)
    while ($stack.Count -gt 0) {
        $current = $stack.Pop()
        foreach ($dir in [System.IO.Directory]::EnumerateDirectories($current)) {
            $name = [System.IO.Path]::GetFileName($dir)
            if ($dir.StartsWith($depsRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
                continue
            }
            if ($name -in @("__pycache__", ".pytest_cache", ".ruff_cache")) {
                Remove-Item -LiteralPath $dir -Recurse -Force
                Write-Host "[clean] $dir"
                continue
            }
            if ($skip -notcontains $name) {
                $stack.Push($dir)
            }
        }
    }
}

switch ($Command) {
    "tree" { Write-ComponentTree }
    "status" { Invoke-CoreStatus }
    "start" { Start-XinYuTarget }
    "stop" { Stop-XinYuTarget }
    "test" { Invoke-CoreTests }
    "smoke" { Invoke-CoreSmoke }
    "verify" { Invoke-XinYuVerify }
    "health" {
        $healthScript = Resolve-XinYuScript "Test-XinYu-StackHealth.ps1"
        if (-not (Test-Path -LiteralPath $healthScript)) {
            throw "Stack health script not found: $healthScript"
        }
        & $healthScript
    }
    "clean" { Invoke-XinYuClean }
}
