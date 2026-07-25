# DRISHTI — start the backend API on http://localhost:8000
# Run from anywhere:  .\start-backend.ps1
$ErrorActionPreference = "Stop"
$backend = Join-Path $PSScriptRoot "backend"
Set-Location $backend

$python = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "No virtualenv found. Creating one and installing dependencies..." -ForegroundColor Yellow
    python -m venv .venv
    & (Join-Path $backend ".venv\Scripts\python.exe") -m pip install --upgrade pip
    & (Join-Path $backend ".venv\Scripts\pip.exe") install -r requirements.txt
}

if (-not (Test-Path (Join-Path $backend "data\mock_data\mock_fir_data.db"))) {
    Write-Host "Generating the Karnataka FIR corpus..." -ForegroundColor Yellow
    & $python scripts\generate_data.py
}
if (-not (Test-Path (Join-Path $backend "data\fir_index.faiss"))) {
    Write-Host "Building the FAISS semantic index..." -ForegroundColor Yellow
    & $python scripts\build_embeddings.py
}

Write-Host ""
Write-Host "DRISHTI API  ->  http://localhost:8000" -ForegroundColor Green
Write-Host "Swagger docs ->  http://localhost:8000/docs" -ForegroundColor DarkGray
Write-Host "(first start takes ~15s while the embedding model loads)" -ForegroundColor DarkGray
Write-Host ""
& $python -m uvicorn main:app --port 8000
