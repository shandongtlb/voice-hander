param(
    [string]$Config = "config.yaml",
    [string]$HostName = "",
    [int]$Port = 0,
    [switch]$Reload,
    [switch]$Install
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "Creating virtual environment at .venv"
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -3 -m venv .venv
    }
    else {
        python -m venv .venv
    }
}

$NeedsInstall = $Install
& $Python -c "import intranet_assistant" *> $null
if ($LASTEXITCODE -ne 0) {
    $NeedsInstall = $true
}

if ($NeedsInstall) {
    Write-Host "Installing/updating project dependencies"
    & $Python -m pip install -e ".[windows]"
}

if (-not (Test-Path $Config) -and (Test-Path "config.example.yaml")) {
    Write-Host "Creating $Config from config.example.yaml"
    Copy-Item "config.example.yaml" $Config
}

$Arguments = @("-m", "intranet_assistant.cli", "serve", "--config", $Config)
if ($HostName -ne "") {
    $Arguments += @("--host", $HostName)
}
if ($Port -gt 0) {
    $Arguments += @("--port", $Port)
}
if ($Reload) {
    $Arguments += "--reload"
}

& $Python @Arguments
