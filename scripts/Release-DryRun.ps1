<#
.SYNOPSIS
  Privacy / release dry-run helpers for XinYu (read-only).

.DESCRIPTION
  Safe, non-destructive checks before a public tag or GitHub Release.
  Does not delete files, push, or modify git history.

  Checks:
  - git status / branch context
  - tracked paths that look like secrets or private runtime
  - optional git archive contents scan (no secrets in export)
  - common token / env patterns in tracked text files (heuristic)

.PARAMETER Archive
  If set, builds a temporary git archive of HEAD and scans the tarball listing
  (and light content samples). Archive is deleted afterward.

.PARAMETER Strict
  Exit non-zero when any high-severity finding is reported.

.EXAMPLE
  .\scripts\Release-DryRun.ps1

.EXAMPLE
  .\scripts\Release-DryRun.ps1 -Archive -Strict
#>
[CmdletBinding()]
param(
    [switch]$Archive,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = if (Test-Path -LiteralPath (Join-Path $ScriptDir "XinYu-Core")) {
    $ScriptDir
} else {
    (Resolve-Path -LiteralPath (Join-Path $ScriptDir "..")).Path
}

Set-Location -LiteralPath $Root

function Write-Section([string]$Title) {
    Write-Host ""
    Write-Host "== $Title ==" -ForegroundColor Cyan
}

function Add-Finding {
    param(
        [ValidateSet("info", "warn", "high")]
        [string]$Severity,
        [string]$Message
    )
    [void]$script:Findings.Add([pscustomobject]@{
        Severity = $Severity
        Message  = $Message
    })
    $color = switch ($Severity) {
        "high" { "Red" }
        "warn" { "Yellow" }
        default { "Gray" }
    }
    Write-Host ("[{0}] {1}" -f $Severity.ToUpperInvariant(), $Message) -ForegroundColor $color
}

$script:Findings = [System.Collections.Generic.List[object]]::new()

Write-Host "XinYu release dry-run (read-only)" -ForegroundColor Green
Write-Host "Root: $Root"

# ── 1. Git context ──────────────────────────────────────────────────────────
Write-Section "Git context"
try {
    $branch = (git rev-parse --abbrev-ref HEAD 2>$null).Trim()
    $head = (git rev-parse --short HEAD 2>$null).Trim()
    $dirty = git status --porcelain
    Write-Host "Branch: $branch"
    Write-Host "HEAD:   $head"
    if ($dirty) {
        Add-Finding -Severity "warn" -Message "Working tree is dirty; release from a clean checkout."
        $dirty | Select-Object -First 20 | ForEach-Object { Write-Host "  $_" }
        if (($dirty | Measure-Object).Count -gt 20) {
            Write-Host "  ... (truncated)"
        }
    } else {
        Add-Finding -Severity "info" -Message "Working tree clean."
    }
} catch {
    Add-Finding -Severity "high" -Message "git not available or not a repository: $_"
}

# ── 2. Tracked path denylist ────────────────────────────────────────────────
Write-Section "Tracked path denylist"
# Private runtime / secrets only — not package source dirs like xinyu_v1/memory/*.py
$pathPatterns = @(
    '(^|/)\.env$',
    '(^|/)[^/]*\.local\.env$',
    'xinyu_qq_gateway\.config\.json$',
    '\.pem$',
    '(^|/)id_rsa',
    '(^|/)examples/agent-apps/xinyu/memory/',
    '(^|/)XinYu-Core/examples/agent-apps/xinyu/memory/',
    '(^|/)XinYu-Core/memory/',
    '(^|/)runtime/deps/',
    '\.xinyu_bridge_token$',
    'credentials\.json$',
    'service-account.*\.json$'
)

$tracked = @(git ls-files)
$badPaths = foreach ($path in $tracked) {
    foreach ($re in $pathPatterns) {
        if ($path -match $re) {
            [pscustomobject]@{ Path = $path; Pattern = $re }
            break
        }
    }
}

if ($badPaths.Count -eq 0) {
    Add-Finding -Severity "info" -Message "No tracked paths matched secret/private denylist patterns."
} else {
    foreach ($hit in $badPaths) {
        Add-Finding -Severity "high" -Message ("Tracked path matches denylist: {0} (/{1}/)" -f $hit.Path, $hit.Pattern)
    }
}

# ── 3. Heuristic content scan (tracked text only, capped) ───────────────────
Write-Section "Heuristic content scan (tracked files)"
$contentPatterns = @(
    @{ Name = "AWS key id";        Re = 'AKIA[0-9A-Z]{16}' },
    @{ Name = "Generic API token"; Re = '(?i)(api[_-]?key|access[_-]?token|secret[_-]?key)\s*[:=]\s*[''"][^''"]{12,}' },
    @{ Name = "Private key block"; Re = '-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----' },
    @{ Name = "Bearer token";      Re = '(?i)bearer\s+[A-Za-z0-9\-_\.]{20,}' },
    @{ Name = "Slack token";       Re = 'xox[baprs]-[0-9A-Za-z-]{10,}' }
)

# Skip bulky / generated / vendored paths even if tracked.
$skipContent = @(
    '(^|/)node_modules/',
    '(^|/)package-lock\.json$',
    '(^|/)\.git/',
    '\.(png|jpg|jpeg|gif|webp|ico|pdf|zip|7z|gz|whl|dll|exe|bin|wasm|mp3|wav|ogg)$'
)

$scanned = 0
$maxFiles = 4000
foreach ($path in $tracked) {
    if ($scanned -ge $maxFiles) {
        Add-Finding -Severity "warn" -Message "Content scan capped at $maxFiles tracked files."
        break
    }
    $skip = $false
    foreach ($re in $skipContent) {
        if ($path -match $re) { $skip = $true; break }
    }
    if ($skip) { continue }

    # Resolve path safely (Chinese / long / odd names must not abort the whole scan).
    $full = $null
    try {
        $norm = ($path -replace '/', [IO.Path]::DirectorySeparatorChar)
        # Strip accidental surrounding quotes from pathological index entries.
        $norm = $norm.Trim().Trim('"')
        $full = [IO.Path]::Combine($Root, $norm)
        if (-not [IO.File]::Exists($full)) { continue }
    } catch {
        continue
    }

    # Skip large files (>1.5 MiB)
    try {
        $item = [IO.FileInfo]::new($full)
        if ($item.Length -gt 1.5MB) { continue }
    } catch {
        continue
    }

    $text = $null
    try {
        $bytes = [System.IO.File]::ReadAllBytes($full)
        # crude binary skip
        $hasNull = $false
        foreach ($b in $bytes) {
            if ($b -eq 0) { $hasNull = $true; break }
        }
        if ($hasNull) { continue }
        $text = [System.Text.Encoding]::UTF8.GetString($bytes)
    } catch {
        continue
    }

    $scanned++
    foreach ($pat in $contentPatterns) {
        if ($text -match $pat.Re) {
            Add-Finding -Severity "high" -Message ("Possible {0} in tracked file: {1}" -f $pat.Name, $path)
        }
    }
}
Add-Finding -Severity "info" -Message "Content-scanned $scanned tracked text files."

# ── 4. Optional git archive ─────────────────────────────────────────────────
if ($Archive) {
    Write-Section "git archive (HEAD)"
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("xinyu-release-dryrun-" + [guid]::NewGuid().ToString("n"))
    New-Item -ItemType Directory -Path $tmp | Out-Null
    $tarPath = Join-Path $tmp "HEAD-archive.tar"
    try {
        git archive --format=tar -o $tarPath HEAD
        if (-not (Test-Path -LiteralPath $tarPath)) {
            Add-Finding -Severity "high" -Message "git archive failed to produce tarball."
        } else {
            $size = (Get-Item -LiteralPath $tarPath).Length
            Add-Finding -Severity "info" -Message ("Archive size: {0:N0} bytes" -f $size)

            # List names via tar if available; else skip listing.
            # Prefer Windows tar.exe — Git Bash tar mis-parses drive letters (C:).
            $tarExe = $null
            foreach ($candidate in @(
                    "$env:SystemRoot\System32\tar.exe",
                    "C:\Windows\System32\tar.exe"
                )) {
                if ($candidate -and (Test-Path -LiteralPath $candidate)) {
                    $tarExe = $candidate
                    break
                }
            }
            if (-not $tarExe) {
                $cmd = Get-Command tar.exe -ErrorAction SilentlyContinue
                if ($cmd -and $cmd.Source -notmatch 'Git\\usr\\bin\\tar') {
                    $tarExe = $cmd.Source
                }
            }
            if ($tarExe) {
                $names = & $tarExe -tf $tarPath 2>$null
                $archiveHits = foreach ($name in $names) {
                    foreach ($re in $pathPatterns) {
                        if ($name -match $re) {
                            [pscustomobject]@{ Path = $name; Pattern = $re }
                            break
                        }
                    }
                }
                if ($archiveHits.Count -eq 0) {
                    Add-Finding -Severity "info" -Message "Archive listing has no denylist path hits."
                } else {
                    foreach ($hit in $archiveHits) {
                        Add-Finding -Severity "high" -Message ("Archive path matches denylist: {0}" -f $hit.Path)
                    }
                }
            } else {
                Add-Finding -Severity "warn" -Message "tar not found; archive created but listing skipped."
            }
        }
    } catch {
        Add-Finding -Severity "high" -Message "git archive step failed: $_"
    } finally {
        Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Section "git archive"
    Write-Host "Skipped (pass -Archive to build and scan a temporary git archive of HEAD)."
}

# ── 5. Suggested manual commands (documentation aid) ────────────────────────
Write-Section "Suggested companion commands (manual)"
@"
# Clean status
git status

# What would a source release include?
git archive --format=tar --prefix=xinyu/ HEAD | tar -tf - | more

# Python deps audit (local)
python -m pip install pip-audit
pip install -e "./XinYu-Core[dev]"
python -m pip_audit

# Desktop audit (local)
cd XinYu_Desktop
npm audit

# Never commit
#   *.env, tokens, memory/, runtime private state, gateway config with secrets
"@ | Write-Host

# ── Summary ─────────────────────────────────────────────────────────────────
Write-Section "Summary"
$high = @($script:Findings | Where-Object { $_.Severity -eq "high" })
$warn = @($script:Findings | Where-Object { $_.Severity -eq "warn" })
Write-Host ("High: {0}  Warn: {1}  Total findings: {2}" -f $high.Count, $warn.Count, $script:Findings.Count)

if ($Strict -and $high.Count -gt 0) {
    Write-Host "Strict mode: failing due to high-severity findings." -ForegroundColor Red
    exit 1
}

Write-Host "Dry-run complete (no files modified)." -ForegroundColor Green
exit 0
