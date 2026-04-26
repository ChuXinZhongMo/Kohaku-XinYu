param(
    [Parameter(Mandatory = $true)]
    [string]$AstrBotRoot,

    [string]$PluginName = "xinyu_bridge"
)

$ErrorActionPreference = "Stop"

$shellRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$source = Join-Path $shellRoot "plugins\$PluginName"

if (-not (Test-Path -LiteralPath $source)) {
    throw "Plugin source not found: $source"
}

$astrRoot = (Resolve-Path -LiteralPath $AstrBotRoot).Path
$pluginsRoot = Join-Path $astrRoot "data\plugins"
$backupRoot = Join-Path $astrRoot "data\plugin_backups"
$target = Join-Path $pluginsRoot $PluginName

New-Item -ItemType Directory -Force -Path $pluginsRoot | Out-Null
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null

if (Test-Path -LiteralPath $target) {
    $backup = Join-Path $backupRoot "$PluginName.backup.$(Get-Date -Format 'yyyyMMddHHmmss')"
    Move-Item -LiteralPath $target -Destination $backup
    Write-Host "Existing plugin moved to $backup"
}

Copy-Item -LiteralPath $source -Destination $target -Recurse
Write-Host "Installed $PluginName to $target"
