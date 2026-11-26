@echo off
chcp 65001 >nul
title HỆ THỐNG CHẤM THI TRẮC NGHIỆM THPT - QM 2025

echo =====================================================================
echo  🚀 ĐANG KHỞI ĐỘNG HỆ THỐNG CHẤM THI TRẮC NGHIỆM THPT (CHUẨN QM 2025)
echo =====================================================================

cd /d "%~dp0"

echo [1/3] Đang giải phóng cổng mạng 8000 (nếu có)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo [2/3] Đang tự động mở trình duyệt tới http://localhost:8000 ...
start "" "http://localhost:8000"

echo [3/3] Đang chạy máy chủ web uvicorn...
python run_server.py

pause
