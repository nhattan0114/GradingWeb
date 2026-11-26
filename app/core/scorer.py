from typing import Dict, Any, List, Tuple
from app.core.models import ExamConfig, ExamKey, StudentGradedResult, QuestionResult

# Bảng điểm phi tuyến tính chuẩn của Bộ Giáo dục & Đào tạo cho Phần II (Đúng/Sai)
# Điểm tối đa mỗi câu là 1.0 điểm nếu đúng cả 4 ý
MOET_PART2_SCORE_TABLE = {
    0: 0.00,
    1: 0.10,
    2: 0.25,
    3: 0.50,
    4: 1.00
}

def calculate_part2_question_score(correct_count: int, max_per_q: float = 1.0) -> float:
    base_score = MOET_PART2_SCORE_TABLE.get(correct_count, 0.00)
    if max_per_q != 1.0:
        return round(base_score * max_per_q, 2)
    return base_score

def grade_student_exam(
    student_id: str,
    file_name: str,
    detected_sbd: str,
    detected_exam_code: str,
    detected_p1: Dict[str, str],
    detected_p2: Dict[str, Dict[str, bool]],
    detected_p3: Dict[str, str],
    flags: Dict[str, str],
    config: ExamConfig,
    annotated_image_url: str = ""
) -> StudentGradedResult:
    """
    Chấm điểm bài thi của học sinh dựa trên ma trận đáp án và quy chế Bộ GD&ĐT 2025.
    """
    exam_key = config.keys.get(detected_exam_code)
    flagged_issues = []
    
    if not exam_key:
        # Nếu không khớp mã đề chuẩn, phân loại thành 'Sai mã đề' để giáo viên đối soát thủ công
        flagged_issues.append(f"Sai mã đề: Mã '{detected_exam_code}' chưa được cấu hình đáp án trong hệ thống.")
        max_possible = config.part1_max_score + config.part2_max_score + config.part3_max_score
        return StudentGradedResult(
            id=student_id,
            file_name=file_name,
            student_sbd=detected_sbd,
            exam_code=detected_exam_code,
            score_part1=0.0,
            score_part2=0.0,
            score_part3=0.0,
            total_score=0.0,
            max_possible_score=max_possible,
            detailed_results=[],
            incorrect_summary=[f"Chưa chấm: Mã đề '{detected_exam_code}' không hợp lệ. Vui lòng chọn mã đề đúng để chấm lại."],
            flagged_issues=flagged_issues,
            annotated_image_url=annotated_image_url
        )

    detailed_results: List[QuestionResult] = []
    incorrect_summary: List[str] = []

    # Thu thập các cờ cảnh báo hệ thống (SBD, Mã đề, Ngoài phạm vi câu hỏi)
    for k, v in flags.items():
        if k in ["SBD", "HANDWRITTEN_SBD", "EXAM_CODE", "FORCED_CODE", "P2_OUT_OF_RANGE"]:
            if v not in flagged_issues:
                flagged_issues.append(v)

    # 1. Chấm Phần I (Trắc nghiệm nhiều lựa chọn - Tuyến tính)
    score_p1 = 0.0
    p1_per_q = config.part1_max_score / max(1, config.part1_num_questions)
    for q_idx in range(1, config.part1_num_questions + 1):
        q_str = str(q_idx)
        stu_ans = detected_p1.get(q_str, "").strip().upper()
        correct_ans = exam_key.part1.get(q_str, "").strip().upper()
        q_flag = flags.get(f"P1_C{q_str}")

        is_corr = (stu_ans == correct_ans) and (correct_ans != "")
        q_score = p1_per_q if is_corr else 0.0
        score_p1 += q_score

        if not is_corr:
            incorrect_summary.append(f"P.I: C{q_str} (tô '{stu_ans or 'trống'}' - ĐA: {correct_ans})")
        if q_flag:
            flagged_issues.append(f"P.I C{q_str}: {q_flag}")

        detailed_results.append(QuestionResult(
            question_num=q_str,
            part=1,
            student_answer=stu_ans,
            correct_answer=correct_ans,
            is_correct=is_corr,
            score=round(q_score, 3),
            max_score=round(p1_per_q, 3),
            flag=q_flag
        ))

    # 2. Chấm Phần II (Đúng/Sai - Phi tuyến tính)
    score_p2 = 0.0
    p2_max_per_q = config.part2_max_score / max(1, config.part2_num_questions)
    for q_idx in range(1, config.part2_num_questions + 1):
        q_str = str(q_idx)
        stu_choices = detected_p2.get(q_str, {})
        key_choices = exam_key.part2.get(q_str, {})
        q_flag = flags.get(f"P2_C{q_str}")

        correct_sub_count = 0
        wrong_subs = []
        is_empty_q = True

        for sub in ['a', 'b', 'c', 'd']:
            stu_val = stu_choices.get(sub)
            key_val = key_choices.get(sub)

            sub_flag = flags.get(f"P2_C{q_str}_{sub}")
            if sub_flag:
                flagged_issues.append(f"P.II C{q_str}: {sub_flag}")

            if stu_val is not None:
                is_empty_q = False
                if key_val is not None and stu_val == key_val:
                    correct_sub_count += 1
                else:
                    wrong_subs.append(sub)
            else:
                wrong_subs.append(f"{sub} (chưa tô)")

        q_score = calculate_part2_question_score(correct_sub_count, max_per_q=p2_max_per_q)
        score_p2 += q_score

        is_all_correct = (correct_sub_count == 4)
        if is_empty_q:
            incorrect_summary.append(f"P.II: C{q_str} (Học sinh để trống toàn bộ câu - đúng 0/4 ý: +0.00đ)")
        elif wrong_subs:
            incorrect_summary.append(f"P.II: C{q_str} (sai ý {', '.join(wrong_subs)} - đúng {correct_sub_count}/4 ý: +{q_score:.2f}đ)")
        
        if q_flag:
            flagged_issues.append(f"P.II C{q_str}: {q_flag}")

        detailed_results.append(QuestionResult(
            question_num=q_str,
            part=2,
            student_answer=stu_choices,
            correct_answer=key_choices,
            is_correct=is_all_correct,
            score=round(q_score, 2),
            max_score=round(p2_max_per_q, 2),
            flag=q_flag
        ))

    # 3. Chấm Phần III (Trả lời ngắn - Tuyến tính)
    score_p3 = 0.0
    p3_per_q = config.part3_max_score / max(1, config.part3_num_questions)
    for q_idx in range(1, config.part3_num_questions + 1):
        q_str = str(q_idx)
        stu_ans = detected_p3.get(q_str, "").strip()
        correct_ans = exam_key.part3.get(q_str, "").strip()
        q_flag = flags.get(f"P3_C{q_str}")

        # Chuẩn hoá so khớp số (ví dụ '3,5' == '3.5', '04' == '4')
        def normalize_val(val: str) -> str:
            v = val.replace(',', '.').strip()
            try:
                f = float(v)
                return f"{f:g}"
            except Exception:
                return v

        is_corr = (normalize_val(stu_ans) == normalize_val(correct_ans)) and (correct_ans != "")
        q_score = p3_per_q if is_corr else 0.0
        score_p3 += q_score

        if not is_corr:
            if not stu_ans:
                incorrect_summary.append(f"P.III: C{q_str} (Học sinh không tô ô tròn nào - ĐA: {correct_ans})")
            else:
                incorrect_summary.append(f"P.III: C{q_str} (tô '{stu_ans}' - ĐA: {correct_ans})")
        if q_flag:
            flagged_issues.append(f"P.III C{q_str}: {q_flag}")

        detailed_results.append(QuestionResult(
            question_num=q_str,
            part=3,
            student_answer=stu_ans,
            correct_answer=correct_ans,
            is_correct=is_corr,
            score=round(q_score, 3),
            max_score=round(p3_per_q, 3),
            flag=q_flag
        ))

    total_score = round(score_p1 + score_p2 + score_p3, 2)

    return StudentGradedResult(
        id=student_id,
        file_name=file_name,
        student_sbd=detected_sbd,
        exam_code=detected_exam_code,
        score_part1=round(score_p1, 2),
        score_part2=round(score_p2, 2),
        score_part3=round(score_p3, 2),
        total_score=total_score,
        max_possible_score=round(config.part1_max_score + config.part2_max_score + config.part3_max_score, 2),
        detailed_results=detailed_results,
        incorrect_summary=incorrect_summary,
        flagged_issues=flagged_issues,
        annotated_image_url=annotated_image_url
    )
