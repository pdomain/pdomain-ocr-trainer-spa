# install.ps1 — install pdomain-ocr-trainer-spa via uv tool install (Windows)
#
# Usage:
#   .\install.ps1              # install from pdomain-index PEP 503 registry (when available)
#   .\install.ps1 .\dist\pdomain_ocr_trainer_spa-*.whl  # install from a local wheel

param(
    [string]$WheelPath = ""
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv not found. Installing..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
}

if ($WheelPath) {
    Write-Host "Installing pdomain-ocr-trainer-spa from $WheelPath ..."
    uv tool install $WheelPath
} else {
    Write-Host "Installing pdomain-ocr-trainer-spa from pdomain-index ..."
    uv tool install `
        --index https://pdomain.github.io/pdomain-index-pip `
        pdomain-ocr-trainer-spa
}

Write-Host ""
Write-Host "✅ pdomain-ocr-trainer-spa installed."
Write-Host "   Run: pdomain-ocr-trainer-ui --port 8081"
