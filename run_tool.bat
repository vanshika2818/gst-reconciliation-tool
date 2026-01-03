@echo off
title GST Reconciliation Tool Launcher
echo ==========================================
echo   Starting GST Reconciliation Tool...
echo ==========================================

:: --- 1. Start Backend Server ---
echo [1/3] Setting up Backend...
cd backend

if not exist venv (
    echo    Creating Python virtual environment...
    python -m venv venv
)

call venv\Scripts\activate
echo    Installing backend dependencies...
pip install -r requirements.txt

echo    Starting Backend Server on Port 5000...
start "GST Backend Server" cmd /k "python app.py"

cd ..

:: --- 2. Start Frontend Server ---
echo [2/3] Setting up Frontend...
cd frontend

:: FORCE INSTALL if node_modules is missing OR if vite is missing
if not exist node_modules (
    echo    First time setup: Installing ALL dependencies...
    call npm install
)

:: SAFETY CHECK: If Vite is still missing, install it explicitly
if not exist node_modules\.bin\vite.cmd (
    echo    [Reparing] Vite not found. Installing Vite manually...
    call npm install vite --save-dev
)

:: Start React App
echo    Starting Frontend Server...
start "GST Frontend Server" cmd /k "npm run dev"

:: --- 3. Open Browser ---
echo [3/3] Launching Browser...
timeout /t 5 > nul
start http://localhost:5173

echo.
echo ==========================================
echo   Tool is running! 
echo   Don't close the two pop-up windows.
echo ==========================================
pause
