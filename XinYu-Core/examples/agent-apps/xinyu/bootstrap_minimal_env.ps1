param(
    [string]$VenvPath = ".venv"
)

$ErrorActionPreference = "Stop"

$xinyuDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $xinyuDir "..\\..\\..")
$venvDir = Join-Path $xinyuDir $VenvPath
$requirements = Join-Path $xinyuDir "requirements-minimal.txt"

Write-Host "Creating minimal Xinyu runtime environment..."
Write-Host "Repo root: $repoRoot"
Write-Host "Xinyu dir:  $xinyuDir"
Write-Host "Venv dir:   $venvDir"

python -m venv $venvDir

$venvPython = Join-Path $venvDir "Scripts\\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Virtual environment Python not found: $venvPython"
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r $requirements

Write-Host ""
Write-Host "Minimal environment is ready."
Write-Host "Next run command:"
Write-Host "  $venvPython $xinyuDir\\run_local_xinyu.py --mode cli"
