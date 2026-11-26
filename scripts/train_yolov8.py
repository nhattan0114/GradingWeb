import os
import sys
import shutil
from pathlib import Path

# Tự động nạp thư viện DLL cho PyTorch trên Windows nếu có
if sys.platform == "win32":
    for p in sys.path:
        torch_lib = os.path.join(p, "torch", "lib")
        if os.path.isdir(torch_lib):
            try:
                os.add_dll_directory(torch_lib)
            except Exception:
                pass

import torch
from ultralytics import YOLO

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_YAML = ROOT_DIR / "datasets" / "qm2025_markers" / "data.yaml"
MODELS_DIR = ROOT_DIR / "app" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("=== BẮT ĐẦU HUẤN LUYỆN YOLOV8-NANO CHO 4 MỐC GÓC PHÔI QM 2025 ===")
    print("PyTorch version:", torch.__version__)
    device = "0" if torch.cuda.is_available() else "cpu"
    print("Thiết bị huấn luyện:", device)

    # Khởi tạo mô hình nền yolov8n.pt
    model = YOLO("yolov8n.pt")

    # Huấn luyện mô hình
    results = model.train(
        data=str(DATA_YAML),
        epochs=35,
        imgsz=640,
        batch=16,
        device=device,
        workers=2,
        fliplr=0.0,  # Không lật ngang vì các mốc góc có tính định hướng TL, TR, BR, BL
        flipud=0.0,  # Không lật dọc
        mosaic=0.5,
        degrees=10.0,
        project=str(ROOT_DIR / "runs" / "train"),
        name="qm2025_markers",
        exist_ok=True,
        verbose=True
    )

    best_weights = ROOT_DIR / "runs" / "train" / "qm2025_markers" / "weights" / "best.pt"
    dest_weights = MODELS_DIR / "yolov8_qm2025_markers.pt"
    
    if best_weights.exists():
        shutil.copy2(best_weights, dest_weights)
        print(f"\n[THÀNH CÔNG] Đã lưu model tốt nhất vào: {dest_weights}")
        print(f"Kích thước model: {dest_weights.stat().st_size / (1024*1024):.2f} MB")
    else:
        print(f"\n[LỖI] Không tìm thấy best weights tại {best_weights}")

if __name__ == "__main__":
    main()
