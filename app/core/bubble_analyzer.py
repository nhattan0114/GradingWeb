"""
Module Phân tích Vết tô Chì (OMR Bubble Analyzer) chuẩn phôi QM 2025.
- Đánh giá tỉ lệ pixel đậm màu trong từng ô tròn.
- Trích xuất SBD, Mã đề, Phần I, Phần II, Phần III.
- Trích xuất ảnh thumbnail viết tay của học sinh (Họ tên, SBD viết tay, Lớp).
"""

from typing import Dict, Tuple, List, Optional, Any
import base64
import numpy as np
import cv2
from app.core.template_qm2025 import QM2025Layout, BUBBLE_RADIUS

class BubbleAnalyzer:
    def __init__(self, layout: Optional[QM2025Layout] = None):
        self.layout = layout or QM2025Layout()

    def evaluate_bubble_fill(self, norm_img: np.ndarray, cx: int, cy: int, radius: int = 9) -> float:
        """
        Tính độ đậm của vết chì trong ô tròn (0.0 đến 255.0, càng nhỏ càng đậm).
        """
        h, w = norm_img.shape[:2]
        r = max(4, radius)
        x1 = max(0, cx - r)
        y1 = max(0, cy - r)
        x2 = min(w, cx + r + 1)
        y2 = min(h, cy + r + 1)

        roi = norm_img[y1:y2, x1:x2]
        if roi.size == 0:
            return 255.0

        mask = np.zeros(roi.shape[:2], dtype=np.uint8)
        rcx, rcy = cx - x1, cy - y1
        cv2.circle(mask, (rcx, rcy), r, 255, -1)

        mean_val = cv2.mean(roi, mask=mask)[0]
        return float(mean_val)

    def extract_header_snippets(self, warped_sheet: np.ndarray) -> Dict[str, str]:
        """
        Cắt ảnh thumbnail thông tin viết tay của học sinh ở phần Header:
        - Họ và tên thí sinh
        - Số báo danh viết tay
        - Lớp
        """
        h, w = warped_sheet.shape[:2]
        snippets = {}

        # 1. Họ và tên
        crop_name = warped_sheet[210:280, 310:880]
        if crop_name.size > 0:
            _, buf = cv2.imencode(".jpg", crop_name, [cv2.IMWRITE_JPEG_QUALITY, 85])
            snippets["name_thumb"] = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"

        # 2. Số báo danh viết tay
        crop_sbd = warped_sheet[270:340, 310:590]
        if crop_sbd.size > 0:
            _, buf = cv2.imencode(".jpg", crop_sbd, [cv2.IMWRITE_JPEG_QUALITY, 85])
            snippets["sbd_thumb"] = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"

        # 3. Lớp
        crop_class = warped_sheet[270:340, 670:880]
        if crop_class.size > 0:
            _, buf = cv2.imencode(".jpg", crop_class, [cv2.IMWRITE_JPEG_QUALITY, 85])
            snippets["class_thumb"] = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"

        return snippets

    def extract_sbd(self, gray_img: np.ndarray) -> Tuple[str, Dict[str, str]]:
        """
        Trích xuất Số Báo Danh (6 chữ số).
        """
        sbd_bubbles = self.layout.get_sbd_bubbles()
        digits = []
        flags = {}

        for col in range(6):
            col_scores = []
            for d in range(10):
                cx, cy = sbd_bubbles[(col, d)]
                score = self.evaluate_bubble_fill(gray_img, cx, cy)
                col_scores.append((d, score))

            col_scores.sort(key=lambda x: x[1]) # tối nhất xếp trước
            top_d, top_score = col_scores[0]
            sec_d, sec_score = col_scores[1]
            col_mean = np.mean([s[1] for s in col_scores])

            if col_mean - top_score < 14:
                digits.append("?")
                flags[f"SBD_col_{col}"] = "Chưa tô rõ số nào"
            else:
                digits.append(str(top_d))

        return "".join(digits), flags

    def extract_exam_code(self, gray_img: np.ndarray) -> Tuple[str, Dict[str, str]]:
        """
        Trích xuất Mã đề thi (3 chữ số).
        """
        code_bubbles = self.layout.get_exam_code_bubbles()
        digits = []
        flags = {}

        for col in range(3):
            col_scores = []
            for d in range(10):
                cx, cy = code_bubbles[(col, d)]
                score = self.evaluate_bubble_fill(gray_img, cx, cy)
                col_scores.append((d, score))

            col_scores.sort(key=lambda x: x[1])
            top_d, top_score = col_scores[0]
            col_mean = np.mean([s[1] for s in col_scores])

            if col_mean - top_score < 14:
                digits.append("?")
                flags[f"ExamCode_col_{col}"] = "Chưa tô rõ ô nào"
            else:
                digits.append(str(top_d))

        return "".join(digits), flags

    def extract_part1(self, gray_img: np.ndarray, num_questions: int = 12) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, Tuple[int, int]]]:
        """
        Trích xuất Phần I: Trắc nghiệm nhiều lựa chọn.
        """
        bubbles = self.layout.get_part1_bubbles(num_questions)
        results = {}
        flags = {}
        chosen_coords = {}

        for q in range(1, num_questions + 1):
            q_str = str(q)
            opt_scores = []
            for opt in ['A', 'B', 'C', 'D']:
                cx, cy = bubbles[(q_str, opt)]
                score = self.evaluate_bubble_fill(gray_img, cx, cy)
                opt_scores.append((opt, score, cx, cy))

            opt_scores.sort(key=lambda x: x[1]) # tối nhất
            top_opt, top_score, top_cx, top_cy = opt_scores[0]
            sec_opt, sec_score, _, _ = opt_scores[1]
            q_mean = np.mean([s[1] for s in opt_scores])

            if q_mean - top_score < 12:
                results[q_str] = ""
                flags[f"P1_C{q_str}"] = "Để trống, không tô đáp án"
            elif sec_score - top_score < 10 and (q_mean - sec_score) > 12:
                results[q_str] = top_opt
                chosen_coords[q_str] = (top_cx, top_cy)
                flags[f"P1_C{q_str}"] = f"Nghi ngờ tô đúp giữa phương án {top_opt} và {sec_opt}"
            else:
                results[q_str] = top_opt
                chosen_coords[q_str] = (top_cx, top_cy)

        return results, flags, chosen_coords

    def extract_part2(self, gray_img: np.ndarray, num_questions: int = 2) -> Tuple[Dict[str, Dict[str, Optional[bool]]], Dict[str, str], Dict[str, Dict[str, Tuple[int, int]]]]:
        """
        Trích xuất Phần II: Đúng / Sai.
        Chuẩn hóa phát hiện vết chì đậm, chống nhận diện nhầm giấy trắng chưa tô.
        """
        bubbles = self.layout.get_part2_bubbles(num_questions)
        results = {}
        flags = {}
        chosen_coords = {}

        for q in range(1, num_questions + 1):
            q_str = str(q)
            results[q_str] = {}
            chosen_coords[q_str] = {}

            for sub in ['a', 'b', 'c', 'd']:
                cx_d, cy_d = bubbles[(q_str, sub, 'D')]
                cx_s, cy_s = bubbles[(q_str, sub, 'S')]

                score_d = self.evaluate_bubble_fill(gray_img, cx_d, cy_d)
                score_s = self.evaluate_bubble_fill(gray_img, cx_s, cy_s)

                diff = abs(score_d - score_s)
                min_val = min(score_d, score_s)
                max_val = max(score_d, score_s)

                # 1. Tô cả 2 ô Đ và S (cả hai đều rất đậm và chênh lệch nhỏ)
                if max_val < 138 and diff < 16:
                    results[q_str][sub] = score_d < score_s
                    flags[f"P2_C{q_str}_{sub}"] = f"Ý {sub} tô cả Đ và S (nghi ngờ tẩy dơ)"
                    chosen_coords[q_str][sub] = (cx_d, cy_d) if score_d < score_s else (cx_s, cy_s)

                # 2. Để trống / Giấy trắng:
                # - Ô tối nhất vẫn quá sáng (> 155): không có vết chì
                # - Hoặc độ chênh lệch giữa Đ và S quá nhỏ (< 14) khi cả hai đều sáng (> 130)
                elif min_val > 155 or (diff < 14 and min_val > 130):
                    results[q_str][sub] = None

                # 3. Có 1 ô được tô chì rõ rệt (đậm hơn ít nhất 14 đơn vị và độ sáng <= 150)
                elif diff >= 14 and min_val <= 150:
                    if score_d < score_s:
                        results[q_str][sub] = True
                        chosen_coords[q_str][sub] = (cx_d, cy_d)
                    else:
                        results[q_str][sub] = False
                        chosen_coords[q_str][sub] = (cx_s, cy_s)

                # 4. Vết chì mấp mé ranh giới mờ
                elif min_val <= 145 and diff >= 10:
                    if score_d < score_s:
                        results[q_str][sub] = True
                        chosen_coords[q_str][sub] = (cx_d, cy_d)
                    else:
                        results[q_str][sub] = False
                        chosen_coords[q_str][sub] = (cx_s, cy_s)
                    flags[f"P2_C{q_str}_{sub}"] = f"Ý {sub} tô hơi mờ"

                else:
                    results[q_str][sub] = None

        # 5. Kiểm tra phát hiện học sinh tô nhầm vào các câu ngoài phạm vi cấu hình đề thi (ví dụ tô ở Câu 3, 4)
        if num_questions < 8:
            all_part2_bubbles = self.layout.get_part2_bubbles(8)
            out_of_range_filled = []
            for out_q in range(num_questions + 1, 9):
                out_q_str = str(out_q)
                filled_count = 0
                for sub in ['a', 'b', 'c', 'd']:
                    cx_d, cy_d = all_part2_bubbles.get((out_q_str, sub, 'D'), (0, 0))
                    cx_s, cy_s = all_part2_bubbles.get((out_q_str, sub, 'S'), (0, 0))
                    if cx_d == 0 or cx_s == 0:
                        continue
                    s_d = self.evaluate_bubble_fill(gray_img, cx_d, cy_d)
                    s_s = self.evaluate_bubble_fill(gray_img, cx_s, cy_s)
                    if min(s_d, s_s) <= 150 and abs(s_d - s_s) >= 14:
                        filled_count += 1
                if filled_count >= 2:
                    out_of_range_filled.append(out_q_str)

            if out_of_range_filled:
                q_names = ", ".join([f"Câu {c}" for c in out_of_range_filled])
                flags["P2_OUT_OF_RANGE"] = f"Học sinh có tô ở {q_names} (ngoài phạm vi {num_questions} câu của đề). Nghi ngờ tô nhầm vị trí câu!"

        return results, flags, chosen_coords

    def extract_part3(self, gray_img: np.ndarray, num_questions: int = 4) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, List[Tuple[int, int]]]]:
        """
        Trích xuất Phần III: Trả lời ngắn.
        """
        bubbles = self.layout.get_part3_bubbles(num_questions)
        results = {}
        flags = {}
        chosen_coords = {}

        for q in range(1, num_questions + 1):
            q_str = str(q)
            col_chars = []
            q_coords = []

            for c_idx in range(4):
                char_scores = []
                if c_idx == 0:
                    cx, cy = bubbles[(q_str, c_idx, '-')]
                    s = self.evaluate_bubble_fill(gray_img, cx, cy, radius=8)
                    char_scores.append(('-', s, cx, cy))
                elif c_idx == 1:
                    cx, cy = bubbles[(q_str, c_idx, ',')]
                    s = self.evaluate_bubble_fill(gray_img, cx, cy, radius=8)
                    char_scores.append((',', s, cx, cy))

                for d in range(10):
                    cx, cy = bubbles[(q_str, c_idx, str(d))]
                    s = self.evaluate_bubble_fill(gray_img, cx, cy, radius=8)
                    char_scores.append((str(d), s, cx, cy))

                char_scores.sort(key=lambda x: x[1])
                top_char, top_score, t_cx, t_cy = char_scores[0]
                col_mean = np.mean([x[1] for x in char_scores])

                if col_mean - top_score > 16:
                    col_chars.append(top_char)
                    q_coords.append((t_cx, t_cy))
                else:
                    col_chars.append("")

            raw_str = "".join(col_chars).strip()
            results[q_str] = raw_str
            chosen_coords[q_str] = q_coords

            if not raw_str:
                flags[f"P3_C{q_str}"] = "Không tô ô tròn nào (Quy chế: không tính chữ viết tay)"

        return results, flags, chosen_coords
