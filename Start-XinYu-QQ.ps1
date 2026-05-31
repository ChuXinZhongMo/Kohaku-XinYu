param(
    [switch]$OpenDashboards,
    [switch]$StrictLlmHttps,
    [switch]$ForceGatewayRestart,
    [ValidateSet("Normal", "Minimized", "Hidden")]
    [string]$NapCatConsoleWindowStyle = "Normal"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Target = Join-Path $Root "scripts\Start-XinYu-QQ.ps1"
if (-not (Test-Path -LiteralPath $Target)) {
    throw "XinYu QQ startup script not found: $Target"
}

$params = @{
    NapCatConsoleWindowStyle = $NapCatConsoleWindowStyle
}
if ($OpenDashboards) { $params.OpenDashboards = $true }
if ($StrictLlmHttps) { $params.StrictLlmHttps = $true }
if ($ForceGatewayRestart) { $params.ForceGatewayRestart = $true }

& $Target @params
