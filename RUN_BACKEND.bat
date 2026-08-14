@echo off
title Red Broadcast - Nesting Backend (Node.js Port 5001)
echo ========================================================
echo   Starting Nesting Node.js Backend Server (Port 5001)
echo ========================================================
cd /d "%~dp0backend"
node server.js
pause
