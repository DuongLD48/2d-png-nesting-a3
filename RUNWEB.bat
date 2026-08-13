@echo off
title Red Broadcast - Local WebApp Engine
echo ========================================================
echo   Starting Red Broadcast Local WebApp (Python app.py)
echo   Listening on http://localhost:8000
echo ========================================================
cd /d "%~dp0"
python app.py
pause
