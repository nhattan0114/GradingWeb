"""
Bản thiết kế mẫu phiếu trả lời trắc nghiệm chuẩn QM 2025 của Bộ GD&ĐT (chuẩn A4 - QM 2025).
Toạ độ hình học chuẩn được hiệu chuẩn từ phôi phiếu thực tế của Bộ GD&ĐT.
"""

from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import cv2

# Kích thước chuẩn A4 tại độ phân giải 200 DPI
SHEET_WIDTH = 1654
SHEET_HEIGHT = 2338

# Toạ độ 4 điểm định vị chuẩn của vùng chấm (Scannable body corners)
# Marker 1 (Top-Left): cạnh Điểm bài thi
# Marker 2 (Top-Right): cạnh Mã đề thi
# Marker 3 (Bottom-Right): góc dưới phải cạnh chữ QM 2025 - A4
# Marker 4 (Bottom-Left): góc dưới trái
SCANNABLE_MARKERS = [
    (200.0, 520.0),    # Top-Left
    (1454.0, 520.0),   # Top-Right
    (1454.0, 2120.0),  # Bottom-Right
    (200.0, 2120.0)    # Bottom-Left
]

BUBBLE_RADIUS = 12 # Bán kính ô tròn tô chì thực tế

class QM2025Layout:
    def __init__(self, width: int = SHEET_WIDTH, height: int = SHEET_HEIGHT):
        self.w = width
        self.h = height

    def get_sbd_bubbles(self) -> Dict[Tuple[int, int], Tuple[int, int]]:
        """
        Toạ độ các ô Số Báo Danh: 6 cột (0..5), 10 hàng (chữ số 0..9).
        Trả về {(col, digit): (cx, cy)}
        """
        cols_x = [1146, 1172, 1196, 1218, 1245, 1273]
        rows_y = [667, 698, 730, 762, 794, 824, 857, 890, 922, 952]
        
        bubbles = {}
        for col_idx, cx in enumerate(cols_x):
            for digit, cy in enumerate(rows_y):
                bubbles[(col_idx, digit)] = (int(cx), int(cy))
        return bubbles

    def get_exam_code_bubbles(self) -> Dict[Tuple[int, int], Tuple[int, int]]:
        """
        Toạ độ các ô Mã Đề Thi: 3 cột (0..2), 10 hàng (chữ số 0..9).
        Trả về {(col, digit): (cx, cy)}
        """
        cols_x = [1351, 1380, 1406]
        rows_y = [667, 698, 730, 762, 794, 824, 857, 890, 922, 952]

        bubbles = {}
        for col_idx, cx in enumerate(cols_x):
            for digit, cy in enumerate(rows_y):
                bubbles[(col_idx, digit)] = (int(cx), int(cy))
        return bubbles

    def get_part1_bubbles(self, num_questions: int = 12) -> Dict[Tuple[str, str], Tuple[int, int]]:
        """
        Phần I: Gồm 4 block (mỗi block 10 câu):
        - Block 1: Câu 1 đến 10
        - Block 2: Câu 11 đến 20 (nếu đề 12 câu thì lấy câu 11 và 12 ở block này)
        - Block 3: Câu 21 đến 30
        - Block 4: Câu 31 đến 40
        Mỗi câu gồm 4 phương án A, B, C, D.
        Trả về {(q_str, option): (cx, cy)}
        """
        blocks_x = [
            [277, 342, 408, 473],   # Block 1 (C1..C10)
            [591, 655, 721, 785],   # Block 2 (C11..C20)
            [901, 965, 1030, 1094], # Block 3 (C21..C30)
            [1212, 1277, 1341, 1407]# Block 4 (C31..C40)
        ]
        rows_y = [1099, 1126, 1154, 1181, 1209, 1236, 1263, 1290, 1318, 1345]
        options = ['A', 'B', 'C', 'D']

        bubbles = {}
        for q in range(1, min(41, num_questions + 1)):
            q_str = str(q)
            block_idx = (q - 1) // 10
            row_idx = (q - 1) % 10

            cy = rows_y[row_idx]
            bx = blocks_x[block_idx]

            for opt_idx, opt in enumerate(options):
                cx = bx[opt_idx]
                bubbles[(q_str, opt)] = (int(cx), int(cy))

        return bubbles

    def get_part2_bubbles(self, num_questions: int = 2) -> Dict[Tuple[str, str, str], Tuple[int, int]]:
        """
        Phần II: Gồm 4 block (mỗi block gồm 2 câu):
        - Block 1: Câu 1 và Câu 2
        - Block 2: Câu 3 và Câu 4
        - Block 3: Câu 5 và Câu 6
        - Block 4: Câu 7 và Câu 8
        Mỗi câu gồm 4 ý a, b, c, d với 2 lựa chọn: Đ (Đúng) và S (Sai).
        Trả về {(q_str, sub_q, choice): (cx, cy)}
        """
        # Toạ độ (cx_d, cx_s) cho mỗi câu trong block:
        # Block 1: Câu 1 (264, 341), Câu 2 (407, 472)
        # Block 2: Câu 3 (578, 655), Câu 4 (721, 786)
        # Block 3: Câu 5 (891, 968), Câu 6 (1034, 1099)
        # Block 4: Câu 7 (1204, 1281), Câu 8 (1347, 1412)
        q_cols = {
            1: (264, 341),
            2: (407, 472),
            3: (578, 655),
            4: (721, 786),
            5: (891, 968),
            6: (1034, 1099),
            7: (1204, 1281),
            8: (1347, 1412)
        }
        rows_y = [1509, 1537, 1565, 1590] # a, b, c, d
        subs = ['a', 'b', 'c', 'd']

        bubbles = {}
        for q in range(1, min(9, num_questions + 1)):
            q_str = str(q)
            cx_d, cx_s = q_cols[q]
            for sub_idx, sub in enumerate(subs):
                cy = rows_y[sub_idx]
                bubbles[(q_str, sub, 'D')] = (int(cx_d), int(cy))
                bubbles[(q_str, sub, 'S')] = (int(cx_s), int(cy))

        return bubbles

    def get_part3_bubbles(self, num_questions: int = 4) -> Dict[Tuple[str, int, str], Tuple[int, int]]:
        """
        Phần III: Gồm 6 cột câu hỏi (Câu 1 đến Câu 6):
        Mỗi câu có 4 cột ký tự:
          - Cột 0: có dấu âm (-) và các số 0-9
          - Cột 1: có dấu phẩy (,) và các số 0-9
          - Cột 2: các số 0-9
          - Cột 3: các số 0-9
        Trả về {(q_str, col_idx, char): (cx, cy)}
        """
        q_base_x = [276, 484, 692, 900, 1108, 1316] # 6 câu
        col_step = 30.0

        sign_y = 1787.0
        y_0 = 1815.0
        y_step = 27.6

        bubbles = {}
        for q in range(1, min(7, num_questions + 1)):
            q_str = str(q)
            base_x = q_base_x[q - 1]

            for c_idx in range(4):
                col_cx = int(base_x + c_idx * col_step)

                # Dấu âm (-) ở cột 0
                if c_idx == 0:
                    bubbles[(q_str, c_idx, '-')] = (col_cx, int(sign_y))
                # Dấu phẩy (,) ở cột 1
                elif c_idx == 1:
                    bubbles[(q_str, c_idx, ',')] = (col_cx, int(sign_y))

                # Chữ số 0..9 ở cả 4 cột
                for d in range(10):
                    cy = int(y_0 + d * y_step)
                    bubbles[(q_str, c_idx, str(d))] = (col_cx, cy)

        return bubbles

def generate_blank_qm2025_sheet(
    num_p1: int = 12,
    num_p2: int = 2,
    num_p3: int = 4
) -> np.ndarray:
    """
    Sinh ảnh phiếu trả lời trắc nghiệm chuẩn Bộ GD&ĐT (chuẩn phôi QM 2025 - A4).
    """
    img = np.full((SHEET_HEIGHT, SHEET_WIDTH, 3), 255, dtype=np.uint8)
    layout = QM2025Layout()

    # 1. Vẽ 4 Marker định vị chuẩn
    for (mx, my) in SCANNABLE_MARKERS:
        cv2.rectangle(img, (int(mx - 15), int(my - 15)), (int(mx + 15), int(my + 15)), (0, 0, 0), -1)

    # 2. Tiêu đề (Header text)
    cv2.putText(img, "BO GIAO DUC VA DAO TAO", (100, 115), cv2.FONT_HERSHEY_DUPLEX, 0.72, (0, 0, 0), 2)
    cv2.putText(img, "PHIEU TRA LOI TRAC NGHIEM - CHUAN QM 2025 (A4)", (100, 145), cv2.FONT_HERSHEY_DUPLEX, 0.85, (0, 40, 120), 2)

    # Khung ghi thông tin học sinh
    cv2.rectangle(img, (100, 195), (int(SHEET_WIDTH * 0.92), 480), (150, 150, 150), 1)
    cv2.putText(img, "1. Hoi dong thi: ................................................................   5. Ky thi: .......................................", (115, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (50, 50, 50), 1)
    cv2.putText(img, "2. Ho va ten thi sinh: .........................................................   6. Ngay thi: ...................................", (115, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (50, 50, 50), 1)
    cv2.putText(img, "3. So bao danh: .............................   4. Lop: ....................   7. Phong thi: .................................", (115, 310), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (50, 50, 50), 1)
    cv2.putText(img, "MON THI: ................................   Ma de thi: [     ]   So phach: [     ]   Giam thi 1: .........   Giam thi 2: .........", (115, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (50, 50, 50), 1)

    # Dòng cắt phách
    cv2.putText(img, "-- 8< -------------------------------------------------------------------------------------------------------------------------", (100, 495), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 120, 120), 1)

    # Khung Điểm bài thi & Số phách
    cv2.rectangle(img, (200, 560), (1000, 980), (0, 0, 0), 1)
    cv2.putText(img, "Diem bai thi (Viet bang so / bang chu)", (220, 600), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

    # Khung Số Báo Danh (SBD) & Mã đề thi
    cv2.rectangle(img, (1120, 560), (1300, 980), (0, 0, 0), 2)
    cv2.putText(img, "7. SO BAO DANH", (1135, 600), cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 0, 0), 2)

    cv2.rectangle(img, (1330, 560), (1430, 980), (0, 0, 0), 2)
    cv2.putText(img, "8. MA DE", (1340, 600), cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 0, 0), 2)

    # Vẽ ô tròn SBD
    sbd_bubbles = layout.get_sbd_bubbles()
    for (col, digit), (cx, cy) in sbd_bubbles.items():
        cv2.circle(img, (cx, cy), BUBBLE_RADIUS, (100, 100, 100), 2)
        cv2.putText(img, str(digit), (cx - 4, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (60, 60, 60), 1)

    # Vẽ ô tròn Mã đề
    code_bubbles = layout.get_exam_code_bubbles()
    for (col, digit), (cx, cy) in code_bubbles.items():
        cv2.circle(img, (cx, cy), BUBBLE_RADIUS, (100, 100, 100), 2)
        cv2.putText(img, str(digit), (cx - 4, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (60, 60, 60), 1)

    # 4. PHẦN I
    cv2.putText(img, "PHAN I: TRAC NGHIEM NHIEU LUA CHON", (200, 1050), cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 50, 130), 2)
    p1_bubbles = layout.get_part1_bubbles(num_p1)
    for (q_str, opt), (cx, cy) in p1_bubbles.items():
        if opt == 'A':
            cv2.putText(img, f"{q_str}", (cx - 30, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
        cv2.circle(img, (cx, cy), BUBBLE_RADIUS, (120, 120, 120), 2)
        cv2.putText(img, opt, (cx - 4, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 80, 80), 1)

    # 5. PHẦN II (Đúng / Sai)
    cv2.putText(img, "PHAN II: TRAC NGHIEM DUNG / SAI", (200, 1460), cv2.FONT_HERSHEY_DUPLEX, 0.65, (130, 40, 0), 2)
    p2_bubbles = layout.get_part2_bubbles(num_p2)
    for (q_str, sub, choice), (cx, cy) in p2_bubbles.items():
        if sub == 'a' and choice == 'D':
            cv2.putText(img, f"Cau {q_str}", (cx - 5, cy - 20), cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 0, 0), 2)
        if choice == 'D':
            cv2.putText(img, f"{sub})", (cx - 24, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
        cv2.circle(img, (cx, cy), BUBBLE_RADIUS, (120, 120, 120), 2)
        cv2.putText(img, choice, (cx - 4, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 80, 80), 1)

    # 6. PHẦN III (Trả lời ngắn)
    cv2.putText(img, "PHAN III: TRAC NGHIEM TRA LOI NGAN", (200, 1660), cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 90, 40), 2)
    p3_bubbles = layout.get_part3_bubbles(num_p3)
    for (q_str, c_idx, char), (cx, cy) in p3_bubbles.items():
        if c_idx == 0 and char == '-':
            cv2.putText(img, f"Cau {q_str}", (cx - 5, cy - 20), cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 0, 0), 2)
        cv2.circle(img, (cx, cy), 11, (120, 120, 120), 1)
        cv2.putText(img, char, (cx - 4, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (80, 80, 80), 1)

    # Chữ ký chân trang
    cv2.putText(img, "QM 2025 - A4", (SHEET_WIDTH - 300, SHEET_HEIGHT - 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 2)

    return img
