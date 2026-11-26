@echo off
chcp 65001 >nul
title HỆ THỐNG CHẤM THI TRẮC NGHIỆM THPT - QM 2025

echo =====================================================================
echo  🚀 KHỞI ĐỘNG HỆ THỐNG CHẤM THI TRẮC NGHIỆM THPT (CHUẨN QM 2025)
echo =====================================================================
echo.

cd /d "%~dp0"

:: 1. Kiểm tra Python trên hệ thống
where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% neq 0 (
        goto :NO_PYTHON
    )
    set "SYS_PYTHON=py"
) else (
    set "SYS_PYTHON=python"
)

:: 2. Kiểm tra hoặc tạo môi trường ảo (venv)
if exist "venv\Scripts\python.exe" (
    set "PY_EXEC=venv\Scripts\python.exe"
    goto :CHECK_MODULES
)

echo [1/4] Chưa tìm thấy môi trường ảo (venv). Đang tự động khởi tạo...
"%SYS_PYTHON%" -m venv venv
if not exist "venv\Scripts\python.exe" (
    echo [CẢNH BÁO] Không thể tạo môi trường ảo 'venv'. Sẽ dùng Python hệ thống.
    set "PY_EXEC=%SYS_PYTHON%"
) else (
    echo [OK] Đã tạo thành công môi trường ảo (venv).
    set "PY_EXEC=venv\Scripts\python.exe"
)

:CHECK_MODULES
:: 3. Kiểm tra các thư viện bắt buộc
echo [2/4] Đang kiểm tra các thư viện phụ thuộc...
"%PY_EXEC%" -c "import fastapi, uvicorn, cv2, ultralytics, openpyxl, pydantic, PIL" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Tất cả các thư viện đã sẵn sàng.
    goto :START_SERVER
)

echo.
echo [THÔNG BÁO] Phát hiện môi trường mới hoặc còn thiếu thư viện trong requirements.txt!
echo [*] Đang tự động tải và cài đặt các thư viện cần thiết...
echo [*] (Quá trình này chỉ chạy lần đầu tiên, có thể mất từ 1 - 3 phút tùy tốc độ mạng)
echo ---------------------------------------------------------------------

"%PY_EXEC%" -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    goto :INSTALL_FAILED
)

echo.
echo [OK] Cài đặt thư viện hoàn tất thành công!

:START_SERVER
echo [3/4] Đang giải phóng cổng mạng 8000 (nếu có ứng dụng khác đang chiếm)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo [4/4] Đang mở trình duyệt tới http://localhost:8000 ...
start "" "http://localhost:8000"

echo.
echo =====================================================================
echo  ĐANG CHẠY MÁY CHỦ WEB UVICORN... (Bấm Ctrl+C để dừng hệ thống)
echo =====================================================================
"%PY_EXEC%" run_server.py
goto :END

:NO_PYTHON
echo.
echo =====================================================================
echo [LỖI] KHÔNG TÌM THẤY PYTHON TRÊN MÁY TÍNH CỦA BẠN!
echo =====================================================================
echo 1. Vui lòng tải và cài đặt Python (phiên bản khuyên dùng: 3.10 - 3.12) tại:
echo    👉 https://www.python.org/downloads/
echo.
echo 2. ⚠️ LƯU Ý RẤT QUAN TRỌNG KHI CÀI ĐẶT:
echo    Ở màn hình cài đặt đầu tiên, bạn HÃY TÍCH CHỌN vào ô:
echo    [x] "Add python.exe to PATH" (hoặc "Add Python to environment variables")
echo    trước khi bấm "Install Now".
echo.
echo 3. Sau khi cài xong Python, hãy mở lại file này (run_web.bat) là xong!
echo =====================================================================
pause
exit /b 1

:INSTALL_FAILED
echo.
echo =====================================================================
echo [LỖI] QUÁ TRÌNH CÀI ĐẶT THƯ VIỆN BỊ GIÁN ĐOẠN HOẶC GẶP LỖI!
echo =====================================================================
echo Hãy kiểm tra lại kết nối mạng Internet của bạn và thử chạy lại file này.
echo Hoặc chạy lệnh thủ công:
echo   %PY_EXEC% -m pip install -r requirements.txt
echo =====================================================================
pause
exit /b 1

:END
pause
