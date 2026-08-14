@echo off
title Red Broadcast - Nesting Fullstack Launcher
echo ========================================================
echo   Starting Both Nesting Servers (Backend + Frontend)
echo ========================================================
echo.
echo [1/2] Launching Backend Node.js Server on port 5001...
start "Nesting Backend (Port 5001)" cmd /k "cd /d "%~dp0backend" && node server.js"

timeout /t 2 > nul

echo [2/2] Launching Frontend Node.js Server on port 3001...
start "Nesting Frontend (Port 3001)" cmd /k "cd /d "%~dp0frontend" && node server.js"

timeout /t 2 > nul

echo.
echo ========================================================
echo   Both servers launched successfully!
echo   Frontend: http://localhost:3001
echo   Backend:  http://localhost:5001
echo ========================================================
start http://localhost:3001
