@echo off
title Red Broadcast - Nesting Frontend (Node.js Port 3001)
echo ========================================================
echo   Starting Nesting Node.js Frontend Server (Port 3001)
echo ========================================================
cd /d "%~dp0frontend"
node server.js
pause
