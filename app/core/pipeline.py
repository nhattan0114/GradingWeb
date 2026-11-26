"""
Pipeline Chấm Thi Trọn Vẹn: Từ Ảnh Gốc Điện Thoại -> Kết Quả Điểm Số & Ảnh Chấm Trực Quan.
- Duy nhất định vị qua 4 ô vuông đen góc chuẩn QM 2025.
- Nếu thiếu góc/lỗi định vị -> Đẩy ngay sang nhóm Lỗi (Sai mã đề / Lỗi quét) kèm giải thích yêu cầu chụp lại.
"""

import base64
import cv2
import numpy as np
from typing import Tuple, Optional
from app.core.template_qm2025 import QM2025Layout
from app.core.preprocessor import warp_perspective_sheet, normalize_illumination
from app.core.bubble_analyzer import BubbleAnalyzer
from app.core.scorer import grade_student_exam
from app.core.annotator import SheetAnnotator
from app.core.models import ExamConfig, StudentGradedResult

class OMRGradingPipeline:
    def __init__(self):
        self.layout = QM2025Layout()
        self.analyzer = BubbleAnalyzer(self.layout)
        self.annotator = SheetAnnotator(self.layout)

    def process_image_bytes(
        self,
        image_bytes: bytes,
        file_name: str,
        config: ExamConfig,
        student_id: str = "",
        force_exam_code: Optional[str] = None
    ) -> Tuple[StudentGradedResult, np.ndarray]:
        """
        Xử lý ảnh từ bytes (tải lên từ browser hoặc smartphone).
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        raw_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if raw_img is None:
            raise ValueError(f"Không thể giải mã file ảnh: {file_name}")

        return self.process_image_cv2(raw_img, file_name, config, student_id, force_exam_code)

    def process_image_cv2(
        self,
        raw_img: np.ndarray,
        file_name: str,
        config: ExamConfig,
        student_id: str = "",
        force_exam_code: Optional[str] = None
    ) -> Tuple[StudentGradedResult, np.ndarray]:
        # 1. Nắn góc phối cảnh dựa DUY NHẤT trên 4 ô vuông đen góc chuẩn QM 2025
        warped_sheet, is_warped_ok, err_msg = warp_perspective_sheet(raw_img)

        # TRƯỜNG HỢP LỖI 1: Không quét được đủ 4 ô vuông đen góc định vị
        if not is_warped_ok or warped_sheet is None:
            annotated_preview = raw_img.copy()
            ph, pw = annotated_preview.shape[:2]
            
            # Vẽ banner cảnh báo màu đỏ nổi bật phía trên ảnh
            bar_h = max(80, int(ph * 0.12))
            cv2.rectangle(annotated_preview, (10, 10), (pw - 10, bar_h), (0, 0, 220), -1)
            cv2.rectangle(annotated_preview, (10, 10), (pw - 10, bar_h), (255, 255, 255), 2)
            cv2.putText(
                annotated_preview,
                "BAI THI LOI: KHONG THE QUET 4 GOC DINH VI",
                (25, int(bar_h * 0.45)),
                cv2.FONT_HERSHEY_DUPLEX,
                max(0.5, 0.7 * (pw / 768.0)),
                (255, 255, 255),
                2
            )
            cv2.putText(
                annotated_preview,
                "YEU CAU: CHUP LAI ANH THAY RO 4 O VUONG DEN GOC",
                (25, int(bar_h * 0.85)),
                cv2.FONT_HERSHEY_DUPLEX,
                max(0.4, 0.6 * (pw / 768.0)),
                (255, 255, 255),
                2
            )

            preview_h = int(annotated_preview.shape[0] * (1100.0 / annotated_preview.shape[1]))
            preview_img = cv2.resize(annotated_preview, (1100, preview_h), interpolation=cv2.INTER_AREA)
            _, buffer = cv2.imencode(".jpg", preview_img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            b64_str = base64.b64encode(buffer).decode("utf-8")

            err_result = StudentGradedResult(
                id=student_id or file_name,
                file_name=file_name,
                student_sbd="CHƯA_RÕ",
                exam_code="LỖI_4_GÓC",
                score_part1=0.0,
                score_part2=0.0,
                score_part3=0.0,
                total_score=0.0,
                max_possible_score=config.part1_max_score + config.part2_max_score + config.part3_max_score,
                detailed_results=[],
                incorrect_summary=[
                    "Không thể chấm điểm: Ảnh chụp không nhận diện được đủ 4 ô vuông đen góc định vị.",
                    "Yêu cầu: Vui lòng chụp lại ảnh bao quát, thẳng góc từ trên xuống và lấy đủ 4 ô vuông đen ở 4 góc bài thi."
                ],
                flagged_issues=[
                    f"LỖI 4 GÓC: {err_msg}"
                ],
                annotated_image_url=f"data:image/jpeg;base64,{b64_str}",
                raw_answers={
                    "p1": {},
                    "p2": {},
                    "p3": {},
                    "detected_code": "LỖI_4_GÓC",
                    "detected_sbd": "CHƯA_RÕ"
                }
            )
            return err_result, annotated_preview

        # 2. Cân bằng sáng & Khử bóng điện thoại (CLAHE)
        gray_sheet = cv2.cvtColor(warped_sheet, cv2.COLOR_BGR2GRAY)
        norm_sheet = normalize_illumination(gray_sheet)

        # 3. Trích xuất thông tin vết tô chì
        header_snippets = self.analyzer.extract_header_snippets(warped_sheet)
        detected_sbd, sbd_flags = self.analyzer.extract_sbd(norm_sheet)
        detected_code, code_flags = self.analyzer.extract_exam_code(norm_sheet)
        detected_p1, p1_flags, p1_coords = self.analyzer.extract_part1(norm_sheet, config.part1_num_questions)
        detected_p2, p2_flags, p2_coords = self.analyzer.extract_part2(norm_sheet, config.part2_num_questions)
        detected_p3, p3_flags, p3_coords = self.analyzer.extract_part3(norm_sheet, config.part3_num_questions)

        all_flags = {}
        all_flags.update(sbd_flags)
        all_flags.update(code_flags)
        all_flags.update(p1_flags)
        all_flags.update(p2_flags)
        all_flags.update(p3_flags)

        # Nếu giáo viên chọn chấm cố định theo mã đề
        effective_code = detected_code
        if force_exam_code and force_exam_code.strip():
            effective_code = force_exam_code.strip()
            if detected_code != effective_code:
                all_flags["FORCED_CODE"] = f"Bài thi tô mã {detected_code}, đã chấm theo mã chỉ định {effective_code}"

        # 4. Chấm điểm theo chuẩn Bộ GD&ĐT 2025
        exam_key = config.keys.get(effective_code)
        graded_result = grade_student_exam(
            student_id=student_id or file_name,
            file_name=file_name,
            detected_sbd=detected_sbd,
            detected_exam_code=effective_code,
            detected_p1=detected_p1,
            detected_p2=detected_p2,
            detected_p3=detected_p3,
            flags=all_flags,
            config=config
        )

        graded_result.grade_level = getattr(config, "grade_level", "Khối 10")

        # Gán ảnh thông tin viết tay và câu trả lời thô
        graded_result.name_thumb = header_snippets.get("name_thumb")
        graded_result.sbd_thumb = header_snippets.get("sbd_thumb")
        graded_result.class_thumb = header_snippets.get("class_thumb")
        graded_result.raw_answers = {
            "p1": detected_p1,
            "p2": detected_p2,
            "p3": detected_p3,
            "detected_code": detected_code,
            "detected_sbd": detected_sbd
        }

        # 5. Vẽ overlay trực quan lên ảnh
        annotated_sheet = self.annotator.annotate(warped_sheet, graded_result, exam_key)

        # Encode ảnh kết quả sang base64 URL cho web hiển thị tức thì
        preview_h = int(annotated_sheet.shape[0] * (1100.0 / annotated_sheet.shape[1]))
        preview_img = cv2.resize(annotated_sheet, (1100, preview_h), interpolation=cv2.INTER_AREA)
        _, buffer = cv2.imencode(".jpg", preview_img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        b64_str = base64.b64encode(buffer).decode("utf-8")
        graded_result.annotated_image_url = f"data:image/jpeg;base64,{b64_str}"

        return graded_result, annotated_sheet
