from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field

class Part1Key(BaseModel):
    answers: Dict[str, str] = Field(default_factory=dict, description="e.g. {'1': 'A', '2': 'C'}")

class Part2QuestionKey(BaseModel):
    a: Optional[bool] = None
    b: Optional[bool] = None
    c: Optional[bool] = None
    d: Optional[bool] = None

class Part2Key(BaseModel):
    answers: Dict[str, Part2QuestionKey] = Field(default_factory=dict)

class Part3Key(BaseModel):
    answers: Dict[str, str] = Field(default_factory=dict, description="e.g. {'1': '-3,5', '2': '42'}")

class ExamKey(BaseModel):
    exam_code: str = Field(..., description="Mã đề thi, e.g. '101'")
    part1: Dict[str, str] = Field(default_factory=dict)
    part2: Dict[str, Dict[str, bool]] = Field(default_factory=dict)
    part3: Dict[str, str] = Field(default_factory=dict)

class ExamConfig(BaseModel):
    exam_id: str = "vat_li_10_gk1"
    grade_level: str = "Khối 10" # "Khối 10", "Khối 11", "Khối 12"
    subject_name: str = "Vật lí 10"
    exam_name: str = "Giữa học kì I"
    academic_year: str = "2026 - 2027"
    school_name: str = "THPT Quế Sơn"
    part1_num_questions: int = 12
    part1_max_score: float = 3.0
    part2_num_questions: int = 2
    part2_max_score: float = 2.0
    part3_num_questions: int = 4
    part3_max_score: float = 2.0
    keys: Dict[str, ExamKey] = Field(default_factory=dict)

class QuestionResult(BaseModel):
    question_num: str
    part: int
    student_answer: Any
    correct_answer: Any
    is_correct: bool
    score: float
    max_score: float
    flag: Optional[str] = None # e.g. "DOUBLE_BUBBLE", "UNCERTAIN_FILL", "EMPTY"

class StudentGradedResult(BaseModel):
    id: str
    file_name: str
    grade_level: Optional[str] = "Khối 10"
    student_name: Optional[str] = ""
    student_class: Optional[str] = ""
    student_sbd: str = ""
    exam_code: str = ""
    score_part1: float = 0.0
    score_part2: float = 0.0
    score_part3: float = 0.0
    total_score: float = 0.0
    max_possible_score: float = 7.0
    detailed_results: List[QuestionResult] = Field(default_factory=list)
    incorrect_summary: List[str] = Field(default_factory=list)
    flagged_issues: List[str] = Field(default_factory=list)
    annotated_image_url: Optional[str] = None
    name_thumb: Optional[str] = None
    class_thumb: Optional[str] = None
    sbd_thumb: Optional[str] = None
    raw_answers: Dict[str, Any] = Field(default_factory=dict)
