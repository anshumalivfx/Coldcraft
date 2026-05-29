$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

function Command-Exists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Host "==> Coldcraft setup (Windows)"

$PythonExe = $null
$PythonArgs = @()

if (Command-Exists "py") {
    $PythonExe = "py"
    $PythonArgs = @("-3.11")
} elseif (Command-Exists "python") {
    $PythonExe = "python"
    $PythonArgs = @()
}

if (-not $PythonExe) {
    if (Command-Exists "winget") {
        Write-Host "==> Installing Python 3.11 via winget"
        winget install --id Python.Python.3.11 -e
        $PythonExe = "py"
        $PythonArgs = @("-3.11")
    } else {
        Write-Host "Python not found and winget is unavailable. Install Python 3.11 manually."
        exit 1
    }
}

Write-Host "==> Creating virtual environment"
& $PythonExe @PythonArgs -m venv .venv

$VenvPython = Join-Path $RootDir ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Virtual environment creation failed."
    exit 1
}

Write-Host "==> Installing Python dependencies"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt

Write-Host "==> Installing Playwright Chromium"
& $VenvPython -m playwright install chromium

if ((Test-Path ".env.example") -and (-not (Test-Path ".env"))) {
    Write-Host "==> Creating .env from .env.example"
    Copy-Item ".env.example" ".env"
}

Write-Host "==> Setup complete"
