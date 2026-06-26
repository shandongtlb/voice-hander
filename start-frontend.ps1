param(
    [switch]$Install,
    [int]$Port = 5173
)

$ErrorActionPreference = "Stop"

$FrontendRoot = Join-Path $PSScriptRoot "frontend"
Set-Location $FrontendRoot

if ($Install -or -not (Test-Path "node_modules")) {
    npm install
}

npm.cmd run dev -- "--port=$Port"
