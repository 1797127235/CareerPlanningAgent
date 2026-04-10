#Requires -Version 5.1
# Career Planning Agent - Quick Launcher
# Double-click to start both backend and frontend

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Career Planning Agent - Starting...  " -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python not found!" -ForegroundColor Red
    Write-Host "Please install Python from https://python.org"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Python: $(python --version 2>&1)" -ForegroundColor Green

# Check Node.js
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Node.js not found!" -ForegroundColor Red
    Write-Host "Please install Node.js from https://nodejs.org"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] npm: $(npm --version 2>&1)" -ForegroundColor Green

# Check files
if (-not (Test-Path "$Root\backend\app.py")) {
    Write-Host "[ERROR] backend\app.py not found" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Backend file found" -ForegroundColor Green

if (-not (Test-Path "$Root\frontend\package.json")) {
    Write-Host "[ERROR] frontend\package.json not found" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Frontend file found" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting services...                  " -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start Backend
Write-Host "[1/2] Starting Backend (port 8000)..." -ForegroundColor Yellow
$backendCmd = "Set-Location '$Root'; python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000; Read-Host 'Press Enter to close'"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Normal

Start-Sleep -Seconds 3

# Start Frontend
Write-Host "[2/2] Starting Frontend (port 5173)..." -ForegroundColor Yellow
$frontendCmd = "Set-Location '$Root\frontend'; npm run dev; Read-Host 'Press Enter to close'"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Normal

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Services Started!                    " -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend API: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Frontend:    http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: Close the two PowerShell windows" -ForegroundColor Yellow
Write-Host "      (Backend/Frontend) to stop services" -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to close this launcher"
