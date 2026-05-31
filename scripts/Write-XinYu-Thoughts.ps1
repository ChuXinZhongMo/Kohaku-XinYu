param(
    [string]$Root = ""
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if (-not $Root) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $WorkspaceRoot = if (Test-Path -LiteralPath (Join-Path $ScriptDir "XinYu-Core")) {
        $ScriptDir
    } else {
        Resolve-Path -LiteralPath (Join-Path $ScriptDir "..")
    }
    $Root = Join-Path $WorkspaceRoot "XinYu-Core\examples\agent-apps\xinyu"
}

$python = Join-Path $Root ".venv\Scripts\python.exe"
$thoughts = Join-Path $Root "xinyu_desktop_thoughts.py"

if (-not (Test-Path -LiteralPath $python)) {
    throw "XinYu Python not found: $python"
}
if (-not (Test-Path -LiteralPath $thoughts)) {
    throw "XinYu thoughts script not found: $thoughts"
}

& $python $thoughts --root $Root
