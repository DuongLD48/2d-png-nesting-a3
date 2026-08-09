@echo off
title Git Clone Setup - 2D PNG Nesting Engine

echo ========================================================
echo   Git Clone Setup - 2D PNG Nesting Engine
echo ========================================================
echo.
echo [1/3] Cloning repository from GitHub...
git clone https://github.com/DuongLD48/2d-png-nesting-a3.git
if errorlevel 1 goto ERROR_GIT

cd 2d-png-nesting-a3

echo.
echo [2/3] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 goto ERROR_PIP

echo.
echo [3/3] Setup Completed Successfully!
echo Running main.py ...
python main.py --config config.json
pause
exit /b 0

:ERROR_GIT
echo.
echo [ERROR] Git clone failed. Please check Git installation or network connection.
pause
exit /b 1

:ERROR_PIP
echo.
echo [ERROR] Dependency installation failed. Please check Python/pip installation.
pause
exit /b 1
