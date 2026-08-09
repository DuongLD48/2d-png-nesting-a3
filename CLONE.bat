@echo off
chcp 65001 > nul
title Git Clone & Setup - 2D PNG Nesting Engine A3

echo ========================================================
echo   Tự Động Clone & Cài Đặt Dự Án 2D PNG Nesting Engine
echo ========================================================
echo.

echo [1/3] Đang clone repository từ GitHub...
git clone https://github.com/DuongLD48/2d-png-nesting-a3.git
if errorlevel 1 (
    echo [LỖI] Không thể clone repository. Vui lòng kiểm tra lại Git hoặc kết nối mạng!
    pause
    exit /b 1
)

cd 2d-png-nesting-a3

echo.
echo [2/3] Đang cài đặt các thư viện Python cần thiết...
pip install -r requirements.txt
if errorlevel 1 (
    echo [LỖI] Cài đặt thư viện thất bại. Vui lòng kiểm tra lại Python và pip!
    pause
    exit /b 1
)

echo.
echo [3/3] Hoàn tất cài đặt thành công!
echo.
echo Nhấn phím bất kỳ để chạy ứng dụng Nesting (main.py)...
pause > nul
python main.py --config config.json
pause
