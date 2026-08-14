@echo off
title 2D PNG Nesting Engine
cd /d "%~dp0"

:MENU
cls
echo ========================================================
echo   2D PNG Nesting Engine - Node.js + Python Runner
echo ========================================================
echo.
echo 1. Run Fullstack Web (Start Backend + Frontend on 2 separate servers)
echo 2. Run Backend Node.js Server Only (Port 5001)
echo 3. Run Frontend Node.js Server Only (Port 3001)
echo 4. Run CLI Nesting Pipeline (Python main.py)
echo 5. Generate Test Data (tests/generate_test_pngs.py)
echo 6. Exit
echo.
set /p choice="Enter choice (1-6): "

if "%choice%"=="1" goto RUN_ALL
if "%choice%"=="2" goto RUN_BACKEND
if "%choice%"=="3" goto RUN_FRONTEND
if "%choice%"=="4" goto RUN_CLI
if "%choice%"=="5" goto RUN_TEST
if "%choice%"=="6" goto END

echo Invalid choice! Please enter 1-6.
timeout /t 2 > nul
goto MENU

:RUN_ALL
call RUN_ALL.bat
goto MENU

:RUN_BACKEND
call RUN_BACKEND.bat
goto MENU

:RUN_FRONTEND
call RUN_FRONTEND.bat
goto MENU

:RUN_CLI
echo.
echo [Running CLI Nesting Pipeline...]
python main.py --config config.json
echo.
pause
goto MENU

:RUN_TEST
echo.
echo [Generating Test PNG Files...]
python tests/generate_test_pngs.py
echo.
pause
goto MENU

:END
exit /b 0