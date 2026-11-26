"""
File khởi chạy máy chủ Chấm Thi Trắc Nghiệm THPT.
Chạy tại: http://localhost:8000
Hỗ trợ cả điện thoại kết nối qua cùng mạng WiFi/LAN.
"""

import os
import sys
import uvicorn
import socket

# Tự động nạp thư viện DLL cho PyTorch trên Windows nếu có
if sys.platform == "win32":
    for p in sys.path:
        torch_lib = os.path.join(p, "torch", "lib")
        if os.path.isdir(torch_lib):
            try:
                os.add_dll_directory(torch_lib)
            except Exception:
                pass

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    local_ip = get_local_ip()
    print("=" * 65)
    print("🚀 HỆ THỐNG CHẤM THI TRẮC NGHIỆM THPT - CHUẨN QM 2025")
    print(f"👉 Truy cập trên Máy tính:  http://localhost:8000")
    print(f"👉 Truy cập trên Điện thoại: http://{local_ip}:8000")
    print("=" * 65)

    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000, reload=False)
