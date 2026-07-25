# DRISHTI — start the web console on http://localhost:5173
# Run from anywhere:  .\start-frontend.ps1
$ErrorActionPreference = "Stop"
$frontend = Join-Path $PSScriptRoot "frontend"
Set-Location $frontend

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    npm install --no-audit --no-fund
}

Write-Host ""
Write-Host "DRISHTI console ->  http://localhost:5173" -ForegroundColor Green
Write-Host "Sign in with     ->  KSP-1054 / drishti" -ForegroundColor DarkGray
Write-Host ""
# Invoked via node directly: npm's .bin shims break on the '&' in this
# project's folder path (they resolve to E:\vite\bin\vite.js and fail).
node node_modules/vite/bin/vite.js
