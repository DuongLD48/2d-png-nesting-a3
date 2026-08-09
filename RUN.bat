@echo off
chcp 65001 > nul
title 2D PNG Nesting Engine A3

echo ========================================================
echo   Ứng Dụng Python 2D PNG Nesting Engine
echo ========================================================
echo.
echo Lựa chọn chế độ chạy:
echo 1. Chạy CLI Nesting Pipeline (main.py)
echo 2. Chạy Giao Diện Web GUI Dashboard (app.py)
echo 3. Sinh dữ liệu PNG mẫu để kiểm thử (tests/generate_test_pngs.py)
echo.
set /p choice="Nhập lựa chọn của bạn (1/2/3): "

if "%choice%"=="1" (
    python main.py --config config.json
) else if "%choice%"=="2" (
    python app.py
) else if "%choice%"=="3" (
    python tests/generate_test_pngs.py
) else (
    echo Lựa chọn không hợp lệ!
)

pause