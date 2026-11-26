@echo off
chcp 65001 >nul
title CÀI ĐẶT MÔI TRƯỜNG - HỆ THỐNG CHẤM THI TRẮC NGHIỆM QM 2025

echo =====================================================================
echo  🛠️ THIẾT LẬP MÔI TRƯỜNG TỰ ĐỘNG CHO HỆ THỐNG CHẤM THI TRẮC NGHIỆM
echo =====================================================================
echo.

cd /d "%~dp0"

where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% neq 0 (
        echo [LỖI] Không tìm thấy Python trên máy tính.
        echo Vui lòng cài đặt Python (3.10 - 3.12) và nhớ tích "Add Python to PATH".
        pause
        exit /b 1
    )
    set "SYS_PYTHON=py"
) else (
    set "SYS_PYTHON=python"
)

if not exist "venv\Scripts\python.exe" (
    echo [1/2] Đang tạo môi trường ảo (venv)...
    "%SYS_PYTHON%" -m venv venv
    if not exist "venv\Scripts\python.exe" (
        echo [LỖI] Không thể tạo thư mục venv.
        pause
        exit /b 1
    )
    echo [OK] Đã tạo môi trường ảo venv thành công.
) else (
    echo [1/2] Đã có môi trường ảo venv.
)

echo.
echo [2/2] Đang cập nhật và cài đặt các thư viện từ requirements.txt...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt

if %errorlevel% equ 0 (
    echo.
    echo =====================================================================
    echo  🎉 THIẾT LẬP HOÀN TẤT! BÂY GIỜ BẠN CÓ THỂ CHẠY FILE 'run_web.bat'.
    echo =====================================================================
) else (
    echo.
    echo [LỖI] Cài đặt thư viện thất bại. Vui lòng kiểm tra lại kết nối mạng.
)

pause
