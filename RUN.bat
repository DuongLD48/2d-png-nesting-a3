@echo off
title 2D PNG Nesting Engine

:MENU
cls
echo ========================================================
echo   2D PNG Nesting Engine - Runner
echo ========================================================
echo.
echo 1. Run CLI Nesting Pipeline (main.py)
echo 2. Run Web GUI Dashboard (app.py)
echo 3. Generate Test Data (tests/generate_test_pngs.py)
echo 4. Exit
echo.
set /p choice="Enter choice (1-4): "

if "%choice%"=="1" goto RUN_CLI
if "%choice%"=="2" goto RUN_WEB
if "%choice%"=="3" goto RUN_TEST
if "%choice%"=="4" goto END

echo Invalid choice! Please enter 1, 2, 3 or 4.
timeout /t 2 > nul
goto MENU

:RUN_CLI
echo.
echo [Running CLI Nesting Pipeline...]
python main.py --config config.json
echo.
pause
goto MENU

:RUN_WEB
echo.
echo [Starting Web GUI Dashboard at http://localhost:8000 ...]
python app.py
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