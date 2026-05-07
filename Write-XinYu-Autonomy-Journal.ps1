param(
    [string]$Root = ""
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if (-not $Root) {
    $WorkspaceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $Root = Join-Path $WorkspaceRoot "XinYu-Core\examples\agent-apps\xinyu"
}

$python = Join-Path $Root ".venv\Scripts\python.exe"
$journal = Join-Path $Root "xinyu_autonomy_journal.py"

if (-not (Test-Path -LiteralPath $python)) {
    throw "XinYu Python not found: $python"
}
if (-not (Test-Path -LiteralPath $journal)) {
    throw "XinYu thoughts script not found: $journal"
}

& $python $journal --root $Root
