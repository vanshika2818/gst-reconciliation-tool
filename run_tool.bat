@echo off
title GST Reconciliation Tool Launcher
echo ==========================================
echo   Starting GST Reconciliation Tool...
echo ==========================================

:: --- 0. CHECK: Is Python Installed? ---
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH!
    echo Please install Python from python.org and check "Add to PATH".
    pause
    exit /b
)

:: --- 1. SETUP BACKEND (Python) ---
echo [1/3] Setting up Backend...
cd backend

:: Create Virtual Env if missing
if not exist venv (
    echo    Creating Python virtual environment...
    python -m venv venv
)

:: Activate and Install Libraries
call venv\Scripts\activate
echo    Installing backend dependencies...
:: This installs: flask, pandas, openpyxl, etc. from your file
pip install -r requirements.txt

:: Start Backend
echo    Starting Backend Server on Port 5000...
start "GST Backend Server" cmd /k "python app.py"

cd ..

:: --- 2. SETUP FRONTEND (Node.js) ---
echo [2/3] Setting up Frontend...
cd frontend

:: Install Modules if missing
if not exist node_modules (
    echo    [First Run] Installing frontend dependencies...
    echo    (This installs React, Axios, Dropzone, etc.)
    call npm install
)

:: --- 3. FORCE INSTALL VITE (The Fix) ---
:: This ensures the build tool is definitely installed
if not exist node_modules\.bin\vite.cmd (
    echo    [Repair] Vite command missing. Installing Vite manually...
    call npm install vite --save-dev
)

:: Start Frontend
echo    Starting Frontend Server...
start "GST Frontend Server" cmd /k "npm run dev"

:: --- 4. LAUNCH BROWSER ---
echo [3/3] Launching Browser...
timeout /t 5 > nul
start http://localhost:5173

echo.
echo ==========================================
echo   Tool is running! 
echo   Don't close the two pop-up windows.
echo ==========================================
pause
