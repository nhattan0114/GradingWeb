"""
Module Tiền xử lý ảnh chuyên dụng cho ảnh chụp bài thi bằng điện thoại (Smartphone photos).
- DUY NHẤT: Nhận diện 4 hình vuông đen góc chuẩn phôi QM 2025 (chuẩn phôi Bộ GD&ĐT).
- Kiểm tra tính hợp lệ hình học (Geometric Validation): tỷ lệ chiều rộng/cao chuẩn, đối xứng.
- Nếu không tìm đủ 4 marker góc hoặc hình học bị sai lệch -> Không đoán mò/không nắn méo,
  trả về lỗi yêu cầu chụp lại bao quát thấy đủ 4 góc định vị.
- Nắn góc phối cảnh (Perspective Warp) đưa về toạ độ chuẩn pixel-perfect (1654 x 2338).
- Khử bóng đổ tay/điện thoại bằng CLAHE thích ứng.
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List
from app.core.template_qm2025 import SHEET_WIDTH, SHEET_HEIGHT
from app.core.marker_detector import MarkerDetectorYOLO

def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Sắp xếp 4 điểm theo thứ tự chuẩn: [top-left, top-right, bottom-right, bottom-left]
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)] # Top-Left
    rect[2] = pts[np.argmax(s)] # Bottom-Right

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)] # Top-Right
    rect[3] = pts[np.argmax(diff)] # Bottom-Left

    return rect

def validate_marker_geometry(pts: np.ndarray) -> bool:
    """
    Kiểm tra 4 điểm góc có tạo thành một hình chữ nhật chuẩn của phôi QM 2025 hay không:
    - 4 cạnh không quá ngắn.
    - Cạnh trên và cạnh dưới có độ dài tương đương (không lệch quá 35%).
    - Cạnh trái và cạnh phải có độ dài tương đương (không lệch quá 35%).
    - Tỷ lệ khung hình (Aspect Ratio = Rộng / Cao) nằm trong khoảng 0.55 đến 1.10 (chuẩn ~0.78).
    """
    tl, tr, br, bl = pts
    w_top = np.linalg.norm(tr - tl)
    w_bot = np.linalg.norm(br - bl)
    h_left = np.linalg.norm(bl - tl)
    h_right = np.linalg.norm(br - tr)

    if min(w_top, w_bot, h_left, h_right) < 40:
        return False

    ratio_w = min(w_top, w_bot) / max(w_top, w_bot)
    ratio_h = min(h_left, h_right) / max(h_left, h_right)
    if ratio_w < 0.65 or ratio_h < 0.65:
        return False

    avg_w = (w_top + w_bot) / 2.0
    avg_h = (h_left + h_right) / 2.0
    aspect = avg_w / avg_h
    if not (0.55 <= aspect <= 1.10):
        return False

    return True

def find_scannable_markers_opencv(image: np.ndarray) -> Optional[np.ndarray]:
    """
    Thuật toán OpenCV truyền thống nhận diện 4 hình vuông đen góc:
    Sử dụng thích ứng Gaussian C, lọc contour solidity & độ tương phản cục bộ.
    """
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 41, 15)
    cnts, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    min_dim = int(min(w, h) * 0.010)
    max_dim = int(min(w, h) * 0.065)

    for c in cnts:
        a = cv2.contourArea(c)
        x, y, cw, ch = cv2.boundingRect(c)
        if min_dim <= cw <= max_dim and min_dim <= ch <= max_dim:
            solidity = a / float(cw * ch)
            ar = cw / float(ch)
            if solidity > 0.55 and 0.60 <= ar <= 1.65:
                pad = 4
                y1, y2 = max(0, y - pad), min(h, y + ch + pad)
                x1, x2 = max(0, x - pad), min(w, x + cw + pad)
                bg_mean = np.mean(gray[y1:y2, x1:x2])
                fg_mean = np.mean(gray[y:y+ch, x:x+cw])
                if fg_mean < bg_mean - 18 and fg_mean < 155:
                    candidates.append((x + cw / 2.0, y + ch / 2.0))

    # Bỏ qua vùng cực trên của ảnh (Header tên trường, tiêu đề phiếu thi)
    candidates = [p for p in candidates if p[1] >= h * 0.12]

    if len(candidates) < 4:
        return None

    mid_x, mid_y = w / 2.0, h / 2.0
    tl = [p for p in candidates if p[0] < mid_x and p[1] < mid_y]
    tr = [p for p in candidates if p[0] >= mid_x and p[1] < mid_y]
    bl = [p for p in candidates if p[0] < mid_x and p[1] >= mid_y]
    br = [p for p in candidates if p[0] >= mid_x and p[1] >= mid_y]

    if not (tl and tr and bl and br):
        return None

    # Mốc chuẩn phôi QM 2025 là mốc ngoài cùng (biên cực đại) ở mỗi góc phần tư
    p_tl = min(tl, key=lambda p: p[0] + p[1])
    p_tr = min(tr, key=lambda p: -p[0] + p[1])
    p_bl = min(bl, key=lambda p: p[0] - p[1])
    p_br = max(br, key=lambda p: p[0] + p[1])

    candidate = np.array([p_tl, p_tr, p_br, p_bl], dtype="float32")
    if validate_marker_geometry(candidate):
        return candidate

    return None

def find_scannable_markers(image: np.ndarray) -> Optional[np.ndarray]:
    """
    Nhận diện 4 hình vuông đen góc chuẩn phôi QM 2025 của Bộ GD&ĐT:
    1. Ưu tiên hàng đầu: Dùng mô hình YOLOv8-nano (MarkerDetectorYOLO) để định vị
       chính xác 4 góc, bỏ qua hoàn toàn mặt bàn gỗ, bóng râm hay chụp nghiêng.
    2. Cơ chế an toàn (Fallback): Nếu YOLO chưa tải được hoặc không phát hiện đủ 4 mốc,
       tự động fallback sang thuật toán lọc hình học OpenCV.
    """
    # 1. Thử nghiệm với YOLOv8-nano
    try:
        detector = MarkerDetectorYOLO()
        if detector.is_available():
            yolo_pts = detector.detect_markers(image, conf_threshold=0.35)
            if yolo_pts is not None and validate_marker_geometry(yolo_pts):
                return yolo_pts
    except Exception as e:
        print(f"[Preprocessor] Warning khi chạy YOLOv8: {e}")

    # 2. Fallback sang OpenCV
    return find_scannable_markers_opencv(image)

def warp_perspective_sheet(image: np.ndarray) -> Tuple[Optional[np.ndarray], bool, str]:
    """
    Nắn góc ảnh chụp điện thoại về kích thước chuẩn A4 (SHEET_WIDTH, SHEET_HEIGHT)
    dựa DUY NHẤT trên 4 Marker góc chuẩn phôi QM 2025.
    
    Trả về:
    - (warped_image, True, "") nếu tìm thấy đủ 4 marker góc hợp lệ.
    - (None, False, error_message) nếu thiếu bất kỳ marker nào hoặc hình học sai lệch.
    """
    marker_pts = find_scannable_markers(image)
    if marker_pts is None:
        return (
            None,
            False,
            "Ảnh chụp không xác định được đủ 4 ô vuông đen góc định vị của phiếu thi QM 2025. "
            "Vui lòng chụp lại ảnh bao quát, thẳng góc từ trên xuống và thấy rõ cả 4 ô vuông đen ở 4 góc bài thi."
        )

    # Toạ độ 4 điểm đích chuẩn trên phôi A4 (SHEET_WIDTH=1654, SHEET_HEIGHT=2338)
    dst_pts = np.array([
        [200.0, 520.0],    # Top-Left: cạnh Điểm bài thi
        [1454.0, 520.0],   # Top-Right: cạnh Mã đề thi
        [1454.0, 2120.0],  # Bottom-Right: góc dưới phải
        [200.0, 2120.0]    # Bottom-Left: góc dưới trái
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(marker_pts, dst_pts)
    warped = cv2.warpPerspective(image, M, (SHEET_WIDTH, SHEET_HEIGHT), flags=cv2.INTER_LANCZOS4)
    return warped, True, ""

def normalize_illumination(gray_sheet: np.ndarray) -> np.ndarray:
    """
    Cân bằng sáng thích ứng và loại bỏ bóng điện thoại (CLAHE).
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray_sheet)
    return enhanced
