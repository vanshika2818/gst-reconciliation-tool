@echo off
title GST Reconciliation Tool Launcher
echo ==========================================
echo   Starting GST Reconciliation Tool...
echo ==========================================

:: --- 1. Start Backend Server ---
echo [1/3] Setting up Backend...
cd backend

:: Create virtual environment if it doesn't exist
if not exist venv (
    echo    Creating Python virtual environment...
    python -m venv venv
)

:: Activate venv and install requirements
call venv\Scripts\activate
echo    Installing backend dependencies (this may take a moment)...
pip install -r requirements.txt > nul 2>&1

:: Start Flask App in a new window
echo    Starting Backend Server on Port 5000...
start "GST Backend Server" cmd /k "python app.py"

:: Go back to root
cd ..

:: --- 2. Start Frontend Server ---
echo [2/3] Setting up Frontend...
cd frontend

:: Install node_modules if missing
if not exist node_modules (
    echo    Installing frontend dependencies...
    call npm install > nul 2>&1
)

:: Start React App in a new window
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