import os
import cv2
import numpy as np
from typing import Optional, Tuple, Dict
from pathlib import Path

# Thêm DLL directory cho PyTorch trên Windows nếu cần
torch_lib = r"C:\Users\LENOVO\AppData\Roaming\Python\Python314\site-packages\torch\lib"
if os.path.exists(torch_lib):
    try:
        os.add_dll_directory(torch_lib)
    except Exception:
        pass

from ultralytics import YOLO

class MarkerDetectorYOLO:
    """
    Detector định vị 4 mốc góc của phiếu thi trắc nghiệm QM 2025 sử dụng YOLOv8-nano.
    Mục tiêu:
    - Bỏ qua 100% nền bàn gỗ, bóng đổ, cạnh giấy bị cong vênh hoặc chụp nghiêng.
    - Nhận diện 4 lớp mốc chuẩn:
        0: marker_tl (Top-Left, cạnh Điểm bài thi)
        1: marker_tr (Top-Right, cạnh Mã đề thi)
        2: marker_br (Bottom-Right, góc dưới phải cạnh QM 2025 - A4)
        3: marker_bl (Bottom-Left, góc dưới trái)
    """
    _instance = None

    def __new__(cls, model_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super(MarkerDetectorYOLO, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_path: Optional[str] = None):
        if getattr(self, "_initialized", False):
            return

        if model_path is None:
            default_path = Path(__file__).resolve().parent.parent / "models" / "yolov8_qm2025_markers.pt"
            self.model_path = str(default_path)
        else:
            self.model_path = model_path

        self.model = None
        if os.path.exists(self.model_path):
            try:
                self.model = YOLO(self.model_path)
                print(f"[MarkerDetectorYOLO] Loaded model successfully: {self.model_path}")
            except Exception as e:
                print(f"[MarkerDetectorYOLO] Lỗi tải model YOLO: {e}")
                self.model = None
        else:
            print(f"[MarkerDetectorYOLO] Model chưa tồn tại tại: {self.model_path}")

        self._initialized = True

    def is_available(self) -> bool:
        return self.model is not None

    def detect_markers(self, image: np.ndarray, conf_threshold: float = 0.40) -> Optional[np.ndarray]:
        """
        Nhận diện 4 mốc góc bằng mô hình YOLOv8-nano.
        Trả về np.ndarray 4x2 theo thứ tự: [p_tl, p_tr, p_br, p_bl] (pixel coordinates float32)
        hoặc None nếu không phát hiện đủ 4 mốc tin cậy.
        """
        if not self.is_available() or image is None:
            return None

        h, w = image.shape[:2]
        
        try:
            # Inference với YOLOv8
            results = self.model.predict(
                image,
                imgsz=640,
                conf=conf_threshold,
                verbose=False
            )
        except Exception as e:
            print(f"[MarkerDetectorYOLO] Lỗi khi inference: {e}")
            return None

        if not results or len(results) == 0:
            return None

        boxes = results[0].boxes
        if len(boxes) < 4:
            return None

        # Thu thập box tốt nhất (confidence cao nhất) cho mỗi class (0..3)
        best_per_class: Dict[int, Tuple[float, float, float]] = {} # cls_id -> (conf, cx, cy)
        
        mid_x, mid_y = w / 2.0, h / 2.0

        for box in boxes:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            if cls_id in (0, 1, 2, 3):
                xywh = box.xywh[0].cpu().numpy()
                cx, cy = float(xywh[0]), float(xywh[1])

                # Kiểm tra góc phần tư tương ứng (Quadrant check)
                if cls_id == 0 and not (cx < mid_x * 1.15 and cy < mid_y * 1.15):
                    continue
                if cls_id == 1 and not (cx >= mid_x * 0.85 and cy < mid_y * 1.15):
                    continue
                if cls_id == 2 and not (cx >= mid_x * 0.85 and cy >= mid_y * 0.85):
                    continue
                if cls_id == 3 and not (cx < mid_x * 1.15 and cy >= mid_y * 0.85):
                    continue

                if cls_id not in best_per_class or conf > best_per_class[cls_id][0]:
                    best_per_class[cls_id] = (conf, cx, cy)

        # Kiểm tra xem có đủ 4 class không
        if len(best_per_class) < 4:
            return None

        # Sắp xếp theo thứ tự chuẩn của phôi QM 2025: [TL, TR, BR, BL]
        p_tl = (best_per_class[0][1], best_per_class[0][2])
        p_tr = (best_per_class[1][1], best_per_class[1][2])
        p_br = (best_per_class[2][1], best_per_class[2][2])
        p_bl = (best_per_class[3][1], best_per_class[3][2])

        candidate = np.array([p_tl, p_tr, p_br, p_bl], dtype="float32")
        return candidate
