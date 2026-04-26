param(
    [string]$VenvPath = ".venv",
    [string]$Mode = "cli",
    [string]$LogLevel = "INFO",
    [string]$LogStderr = "auto",
    [string]$Llm = "",
    [string]$ApiKey = "",
    [string]$BaseUrl = "",
    [switch]$NoSession
)

$ErrorActionPreference = "Stop"

$xinyuDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $xinyuDir "$VenvPath\\Scripts\\python.exe"
$launcher = Join-Path $xinyuDir "run_local_xinyu.py"
$localEnv = Join-Path $xinyuDir "xinyu.local.env"

if (-not (Test-Path $venvPython)) {
    throw "Virtual environment Python not found: $venvPython"
}

if ($ApiKey) {
    $env:XINYU_API_KEY = $ApiKey
}
if ($BaseUrl) {
    $env:XINYU_BASE_URL = $BaseUrl
}
elseif ((-not $env:XINYU_API_KEY) -and (Test-Path $localEnv)) {
    Get-Content -LiteralPath $localEnv | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            return
        }
        $parts = $line.Split("=", 2)
        $key = $parts[0].Trim()
        $value = $parts[1].Trim().Trim('"').Trim("'")
        if ($key -and -not [Environment]::GetEnvironmentVariable($key, "Process")) {
            Set-Item -Path ("Env:" + $key) -Value $value
        }
    }
}

$args = @($launcher, "--mode", $Mode, "--log-level", $LogLevel, "--log-stderr", $LogStderr)
if ($Llm) {
    $args += @("--llm", $Llm)
}
if ($NoSession) {
    $args += "--no-session"
}

& $venvPython @args
