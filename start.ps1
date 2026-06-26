param(
    [string]$Config = "config.yaml",
    [string]$HostName = "",
    [int]$Port = 0,
    [switch]$Reload,
    [switch]$Install
)

$Script = Join-Path $PSScriptRoot "scripts\start.ps1"
& $Script @PSBoundParameters
