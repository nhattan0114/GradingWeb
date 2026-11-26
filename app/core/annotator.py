"""
Module Trực quan hoá bài chấm (Visual Annotator).
Vẽ kết quả chấm đè lên ảnh bài thi:
- Ô khoanh Xanh lá: Học sinh tô ĐÚNG.
- Ô khoanh Đỏ: Học sinh tô SAI.
- Ô khoanh Cam/Vàng: Đáp án chuẩn của câu học sinh làm sai.
- Hộp cảnh báo Vàng: Ô nghi ngờ tô đúp hoặc tẩy dơ.
- In Tổng điểm & SBD to rõ ở góc trên cùng bài thi.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Any
from app.core.template_qm2025 import QM2025Layout, BUBBLE_RADIUS
from app.core.models import StudentGradedResult, ExamKey

COLOR_CORRECT = (46, 175, 75)      # Xanh lá cây (BGR: (G, R, B) -> cv2 là B, G, R) -> (46, 180, 50)
COLOR_WRONG = (30, 30, 220)        # Đỏ
COLOR_KEY = (0, 140, 255)          # Cam / Vàng
COLOR_FLAG = (0, 215, 255)         # Vàng cảnh báo

class SheetAnnotator:
    def __init__(self, layout: Optional[QM2025Layout] = None):
        self.layout = layout or QM2025Layout()

    def annotate(
        self,
        warped_sheet: np.ndarray,
        graded_result: StudentGradedResult,
        exam_key: Optional[ExamKey] = None
    ) -> np.ndarray:
        """
        Vẽ overlay trực quan lên ảnh bài thi đã được nắn thẳng.
        """
        annotated = warped_sheet.copy()
        n_p1 = len([q for q in graded_result.detailed_results if q.part == 1]) or 12
        n_p2 = len([q for q in graded_result.detailed_results if q.part == 2]) or 2
        n_p3 = len([q for q in graded_result.detailed_results if q.part == 3]) or 4
        p1_bubbles = self.layout.get_part1_bubbles(n_p1)
        p2_bubbles = self.layout.get_part2_bubbles(n_p2)
        p3_bubbles = self.layout.get_part3_bubbles(n_p3)

        # 1. Overlay Header: Điểm số & SBD
        # Vẽ banner điểm số ở góc trên bên trái
        cv2.rectangle(annotated, (100, 390), (550, 470), (245, 245, 245), -1)
        cv2.rectangle(annotated, (100, 390), (550, 470), (0, 100, 200), 2)
        score_text = f"DIEM: {graded_result.total_score:.2f} / {graded_result.max_possible_score:.1f}"
        cv2.putText(annotated, score_text, (115, 445), cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 30, 180), 3)

        # 2. Vẽ Phần I
        for q_res in graded_result.detailed_results:
            if q_res.part == 1:
                q_str = q_res.question_num
                stu_opt = q_res.student_answer
                key_opt = q_res.correct_answer

                # Ô đáp án đúng (vẽ vòng tròn cam mỏng)
                if key_opt and (q_str, key_opt) in p1_bubbles:
                    k_cx, k_cy = p1_bubbles[(q_str, key_opt)]
                    cv2.circle(annotated, (k_cx, k_cy), BUBBLE_RADIUS + 4, (0, 165, 255), 2)

                # Ô học sinh chọn
                if stu_opt and (q_str, stu_opt) in p1_bubbles:
                    s_cx, s_cy = p1_bubbles[(q_str, stu_opt)]
                    if q_res.is_correct:
                        cv2.circle(annotated, (s_cx, s_cy), BUBBLE_RADIUS + 2, (40, 190, 60), 3)
                    else:
                        cv2.circle(annotated, (s_cx, s_cy), BUBBLE_RADIUS + 2, (30, 30, 230), 3)
                        # Dấu X
                        cv2.line(annotated, (s_cx - 8, s_cy - 8), (s_cx + 8, s_cy + 8), (30, 30, 230), 2)
                        cv2.line(annotated, (s_cx + 8, s_cy - 8), (s_cx - 8, s_cy + 8), (30, 30, 230), 2)

        # 3. Vẽ Phần II
        for q_res in graded_result.detailed_results:
            if q_res.part == 2:
                q_str = q_res.question_num
                stu_dict = q_res.student_answer or {}
                key_dict = q_res.correct_answer or {}

                for sub in ['a', 'b', 'c', 'd']:
                    stu_val = stu_dict.get(sub)
                    key_val = key_dict.get(sub)

                    # Vẽ đáp án đúng (cam)
                    if key_val is not None:
                        k_choice = 'D' if key_val else 'S'
                        if (q_str, sub, k_choice) in p2_bubbles:
                            k_cx, k_cy = p2_bubbles[(q_str, sub, k_choice)]
                            cv2.circle(annotated, (k_cx, k_cy), BUBBLE_RADIUS + 3, (0, 165, 255), 2)

                    # Vẽ ô học sinh chọn
                    if stu_val is not None:
                        s_choice = 'D' if stu_val else 'S'
                        if (q_str, sub, s_choice) in p2_bubbles:
                            s_cx, s_cy = p2_bubbles[(q_str, sub, s_choice)]
                            if stu_val == key_val:
                                cv2.circle(annotated, (s_cx, s_cy), BUBBLE_RADIUS + 2, (40, 190, 60), 3)
                            else:
                                cv2.circle(annotated, (s_cx, s_cy), BUBBLE_RADIUS + 2, (30, 30, 230), 3)
                                cv2.line(annotated, (s_cx - 7, s_cy - 7), (s_cx + 7, s_cy + 7), (30, 30, 230), 2)
                                cv2.line(annotated, (s_cx + 7, s_cy - 7), (s_cx - 7, s_cy + 7), (30, 30, 230), 2)

        # 3b. Cảnh báo trực quan nếu học sinh tô vào các câu ngoài phạm vi đề thi ở Phần II (ví dụ tô Câu 3, 4 khi đề chỉ có 2 câu)
        p2_warning = next((flag for flag in (graded_result.flagged_issues or []) if "ngoài phạm vi" in flag.lower() or "nghi ngờ tô nhầm vị trí câu" in flag.lower()), None)
        if p2_warning:
            q_cols = {
                1: (264, 341), 2: (407, 472),
                3: (578, 655), 4: (721, 786),
                5: (891, 968), 6: (1034, 1099),
                7: (1204, 1281), 8: (1347, 1412)
            }
            for out_q in range(n_p2 + 1, 9):
                if f"Câu {out_q}" in p2_warning:
                    c_left, c_right = q_cols[out_q]
                    x1 = c_left - 20
                    x2 = c_right + 20
                    y1 = 1485
                    y2 = 1615
                    # Vẽ khung nét màu cam/vàng cảnh báo
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 140, 255), 2)
                    cv2.putText(annotated, f"! C{out_q} NGOAI DE !", (x1 - 10, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 30, 220), 2)

        # 4. Vẽ Phần III
        for q_res in graded_result.detailed_results:
            if q_res.part == 3:
                q_str = q_res.question_num
                # Hiển thị text điểm ngay trên câu hỏi
                cx_ref, cy_ref = p3_bubbles.get((q_str, 0, '0'), (200, 1800))
                tag = f"+{q_res.score:.2f}d" if q_res.is_correct else f"0d (DA: {q_res.correct_answer})"
                color = (40, 190, 60) if q_res.is_correct else (30, 30, 230)
                cv2.putText(annotated, tag, (cx_ref + 40, cy_ref - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)

        return annotated
