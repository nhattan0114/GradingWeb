"""
FastAPI Server phục vụ Hệ Thống Chấm Điểm Thi Trắc Nghiệm THPT (Chuẩn QM 2025).
- Tải lên ảnh bài thi hàng loạt từ điện thoại/máy tính
- Chấm điểm tự động chuẩn Bộ GD&ĐT (Phần I, II, III)
- Quản lý riêng biệt từng Mã đề, gom các bài 'Sai mã đề' thành nhóm riêng (không tạo mã đề ảo)
- Hỗ trợ đổi mã đề và chấm lại tức thì (Regrade)
- Tự động lưu trữ dữ liệu bền vững (Persistence) vào thư mục /data (không mất khi tắt server)
- Xuất báo cáo điểm chuyên nghiệp ra Excel (.xlsx đa Sheet) và Word (.docx)
"""

import os
import sys

# Tự động nạp thư viện DLL cho PyTorch trên Windows nếu có
if sys.platform == "win32":
    for p in sys.path:
        torch_lib = os.path.join(p, "torch", "lib")
        if os.path.isdir(torch_lib):
            try:
                os.add_dll_directory(torch_lib)
            except Exception:
                pass

import uuid
import json
import io
import csv
import re
import unicodedata
from typing import List, Optional, Dict, Union, Any
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException, Body
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.models import ExamConfig, ExamKey, StudentGradedResult
from app.core.pipeline import OMRGradingPipeline
from app.core.scorer import grade_student_exam
from app.core.template_qm2025 import generate_blank_qm2025_sheet

app = FastAPI(
    title="Chấm Thi Trắc Nghiệm THPT - Chuẩn QM 2025",
    description="Hệ thống chấm thi trắc nghiệm A4 theo mẫu mới nhất của Bộ GD&ĐT",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_header(request, call_next):
    response = await call_next(request)
    # Ngăn trình duyệt Chrome/Edge lưu cache file tĩnh và API để luôn hiển thị giao diện mới nhất
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

pipeline = OMRGradingPipeline()

# =============================================================================
# CẤU HÌNH ĐỀ THI VÀ MA TRẬN ĐÁP ÁN THEO KHỐI (10, 11, 12)
# =============================================================================
GRADES = ["Khối 10", "Khối 11", "Khối 12"]
current_grade: str = "Khối 10"

# Đáp án mặc định cho các mã đề 201..204 của bộ đề mẫu
default_keys_201_204 = {
    "201": ExamKey(
        exam_code="201",
        part1={
            "1": "A", "2": "C", "3": "A", "4": "A", "5": "A", "6": "C",
            "7": "B", "8": "B", "9": "D", "10": "B", "11": "C", "12": "D"
        },
        part2={
            "1": {"a": True, "b": True, "c": False, "d": False},
            "2": {"a": False, "b": False, "c": True, "d": True}
        },
        part3={
            "1": "4", "2": "1", "3": "6,5", "4": "3"
        }
    ),
    "202": ExamKey(
        exam_code="202",
        part1={
            "1": "B", "2": "B", "3": "D", "4": "D", "5": "A", "6": "C",
            "7": "B", "8": "C", "9": "D", "10": "C", "11": "A", "12": "D"
        },
        part2={
            "1": {"a": False, "b": True, "c": True, "d": False},
            "2": {"a": False, "b": True, "c": False, "d": True}
        },
        part3={
            "1": "14", "2": "0,5", "3": "8,5", "4": "1,5"
        }
    ),
    "203": ExamKey(
        exam_code="203",
        part1={
            "1": "C", "2": "A", "3": "C", "4": "B", "5": "B", "6": "D",
            "7": "A", "8": "A", "9": "A", "10": "B", "11": "D", "12": "C"
        },
        part2={
            "1": {"a": False, "b": False, "c": True, "d": True},
            "2": {"a": True, "b": True, "c": False, "d": False}
        },
        part3={
            "1": "6,5", "2": "3", "3": "4", "4": "1"
        }
    ),
    "204": ExamKey(
        exam_code="204",
        part1={
            "1": "B", "2": "D", "3": "C", "4": "C", "5": "C", "6": "D",
            "7": "B", "8": "D", "9": "A", "10": "B", "11": "D", "12": "A"
        },
        part2={
            "1": {"a": False, "b": True, "c": False, "d": True},
            "2": {"a": False, "b": True, "c": True, "d": False}
        },
        part3={
            "1": "8,5", "2": "1,5", "3": "14", "4": "0,5"
        }
    )
}

configs_by_grade: Dict[str, ExamConfig] = {
    "Khối 10": ExamConfig(
        exam_id="vat_li_10_gk1",
        grade_level="Khối 10",
        subject_name="Vật lí 10",
        exam_name="Giữa học kì I",
        academic_year="2026 - 2027",
        school_name="Trường THPT Quế Sơn",
        enable_handwriting_ocr=False,
        part1_num_questions=12,
        part1_max_score=3.0,
        part2_num_questions=2,
        part2_max_score=2.0,
        part3_num_questions=4,
        part3_max_score=2.0,
        keys=default_keys_201_204
    ),
    "Khối 11": ExamConfig(
        exam_id="vat_li_11_gk1",
        grade_level="Khối 11",
        subject_name="Vật lí 11",
        exam_name="Giữa học kì I",
        academic_year="2026 - 2027",
        school_name="Trường THPT Quế Sơn",
        enable_handwriting_ocr=False,
        part1_num_questions=12,
        part1_max_score=3.0,
        part2_num_questions=2,
        part2_max_score=2.0,
        part3_num_questions=4,
        part3_max_score=2.0,
        keys={
            "101": ExamKey(
                exam_code="101",
                part1={"1": "A", "2": "B", "3": "C", "4": "D", "5": "A", "6": "B", "7": "C", "8": "D", "9": "A", "10": "B", "11": "C", "12": "D"},
                part2={"1": {"a": True, "b": False, "c": True, "d": False}, "2": {"a": False, "b": True, "c": False, "d": True}},
                part3={"1": "12", "2": "3,5", "3": "0,8", "4": "25"}
            )
        }
    ),
    "Khối 12": ExamConfig(
        exam_id="vat_li_12_gk1",
        grade_level="Khối 12",
        subject_name="Vật lí 12",
        exam_name="Giữa học kì I",
        academic_year="2026 - 2027",
        school_name="Trường THPT Quế Sơn",
        enable_handwriting_ocr=False,
        part1_num_questions=12,
        part1_max_score=3.0,
        part2_num_questions=2,
        part2_max_score=2.0,
        part3_num_questions=4,
        part3_max_score=2.0,
        keys={
            "301": ExamKey(
                exam_code="301",
                part1={"1": "A", "2": "C", "3": "D", "4": "B", "5": "B", "6": "C", "7": "A", "8": "D", "9": "C", "10": "A", "11": "B", "12": "D"},
                part2={"1": {"a": False, "b": True, "c": True, "d": False}, "2": {"a": True, "b": False, "c": True, "d": False}},
                part3={"1": "4", "2": "2,5", "3": "100", "4": "1,2"}
            )
        }
    )
}

current_config: ExamConfig = configs_by_grade[current_grade]

# Danh sách kết quả bài thi đã chấm
graded_records: Dict[str, StudentGradedResult] = {}

# =============================================================================
# HỆ THỐNG LƯU TRỮ DỮ LIỆU BỀN VỮNG (PERSISTENCE)
# =============================================================================
def save_data_to_disk():
    """Lưu toàn bộ cấu hình theo từng khối và kết quả bài thi đã chấm vào ổ đĩa."""
    try:
        # 1. Lưu config theo từng khối
        for g_name, cfg in configs_by_grade.items():
            slug = g_name.replace(" ", "_").lower()
            with open(os.path.join(DATA_DIR, f"config_{slug}.json"), "w", encoding="utf-8") as f:
                f.write(cfg.model_dump_json(indent=2))

        # Lưu active config vào config.json
        with open(os.path.join(DATA_DIR, "config.json"), "w", encoding="utf-8") as f:
            f.write(current_config.model_dump_json(indent=2))
        
        # 2. Lưu danh sách kết quả bài thi
        with open(os.path.join(DATA_DIR, "results.json"), "w", encoding="utf-8") as f:
            records_list = [r.model_dump() for r in graded_records.values()]
            json.dump(records_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[CẢNH BÁO] Lỗi lưu trữ dữ liệu vào đĩa: {e}")

def load_data_from_disk():
    """Tự động khôi phục dữ liệu từ thư mục /data khi khởi động lại máy chủ."""
    global current_config, current_grade, configs_by_grade, graded_records
    
    # 1. Khôi phục cấu hình từng khối
    for g_name in GRADES:
        slug = g_name.replace(" ", "_").lower()
        cfg_file = os.path.join(DATA_DIR, f"config_{slug}.json")
        if os.path.exists(cfg_file):
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    configs_by_grade[g_name] = ExamConfig(**json.load(f))
                    print(f"[KHÔI PHỤC] Đã tải cấu hình {g_name} từ {cfg_file}")
            except Exception as e:
                print(f"[CẢNH BÁO] Không thể đọc {cfg_file}: {e}")

    # Chỉ khôi phục từ config.json cũ nếu chưa có tệp cấu hình riêng của Khối 10
    cfg_legacy = os.path.join(DATA_DIR, "config.json")
    cfg_k10 = os.path.join(DATA_DIR, "config_khối_10.json")
    if os.path.exists(cfg_legacy) and not os.path.exists(cfg_k10) and "Khối 10" in configs_by_grade:
        try:
            with open(cfg_legacy, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["grade_level"] = "Khối 10"
                if "12" in data.get("subject_name", ""):
                    data["subject_name"] = "Vật lí 10"
                configs_by_grade["Khối 10"] = ExamConfig(**data)
        except Exception as e:
            pass

    current_config = configs_by_grade.get(current_grade, configs_by_grade["Khối 10"])

    # 2. Khôi phục bài thi đã chấm
    results_file = os.path.join(DATA_DIR, "results.json")
    if os.path.exists(results_file):
        try:
            with open(results_file, "r", encoding="utf-8") as f:
                raw_results = json.load(f)
                graded_records.clear()
                for it in raw_results:
                    r = StudentGradedResult(**it)
                    graded_records[r.id] = r
                print(f"[KHÔI PHỤC] Đã nạp lại {len(graded_records)} bài thi từ phiên làm việc trước!")
        except Exception as e:
            print(f"[CẢNH BÁO] Không thể đọc {results_file}: {e}")

# Tải dữ liệu ngay khi import module
load_data_from_disk()

# =============================================================================
# REST API ENDPOINTS
# =============================================================================
class UpdateStudentInfo(BaseModel):
    student_sbd: Optional[str] = None

@app.get("/api/grades")
def get_grades_list():
    return {
        "grades": GRADES,
        "current_grade": current_grade
    }

@app.post("/api/grades/select")
def select_current_grade(grade: str = Form(...)):
    global current_grade, current_config
    g = grade.strip()
    if g in ["10", "11", "12"]:
        g = f"Khối {g}"
    if g not in GRADES:
        raise HTTPException(status_code=400, detail=f"Khối không hợp lệ: {grade}")
    current_grade = g
    current_config = configs_by_grade[current_grade]
    save_data_to_disk()
    return {"status": "success", "current_grade": current_grade, "config": current_config}

@app.get("/api/config")
def get_config(grade: Optional[str] = Query(None)):
    if grade:
        g = grade.strip()
        if g in ["10", "11", "12"]:
            g = f"Khối {g}"
        if g in configs_by_grade:
            return configs_by_grade[g]
    return current_config

@app.post("/api/config")
def update_config(config: ExamConfig, grade: Optional[str] = Query(None)):
    global current_config, configs_by_grade
    g = grade or config.grade_level or current_grade
    if g in ["10", "11", "12"]:
        g = f"Khối {g}"
    config.grade_level = g
    configs_by_grade[g] = config
    if g == current_grade:
        current_config = config
    save_data_to_disk()
    return {"status": "success", "message": f"Đã cập nhật cấu hình đề thi cho {g}", "grade": g}

@app.post("/api/config/rename-code")
def rename_exam_code(
    old_code: str = Form(...),
    new_code: str = Form(...),
    grade: Optional[str] = Form(None)
):
    global configs_by_grade, current_config, graded_records
    g = grade or current_grade
    if g in ["10", "11", "12"]:
        g = f"Khối {g}"
    cfg = configs_by_grade.get(g, current_config)
    
    old_c = old_code.strip()
    new_c = new_code.strip()
    if not old_c or not new_c:
        raise HTTPException(status_code=400, detail="Mã đề không được để trống")
    if old_c not in cfg.keys:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy Mã đề {old_c} trong {g}")
    if new_c in cfg.keys and new_c != old_c:
        raise HTTPException(status_code=400, detail=f"Mã đề {new_c} đã tồn tại trong {g}")

    key_data = cfg.keys.pop(old_c)
    key_data.exam_code = new_c
    cfg.keys[new_c] = key_data

    # Cập nhật các bài thi có mã đề cũ sang mã mới
    updated_records_count = 0
    for r in graded_records.values():
        if (getattr(r, "grade_level", None) == g or not getattr(r, "grade_level", None)) and r.exam_code == old_c:
            r.exam_code = new_c
            updated_records_count += 1

    save_data_to_disk()
    return {
        "status": "success",
        "message": f"Đã đổi Mã đề {old_c} thành {new_c} thành công",
        "old_code": old_c,
        "new_code": new_c,
        "updated_records": updated_records_count,
        "config": cfg
    }

@app.delete("/api/config/keys/{exam_code}")
def delete_exam_code(exam_code: str, grade: Optional[str] = Query(None)):
    global configs_by_grade, current_config
    g = grade or current_grade
    if g in ["10", "11", "12"]:
        g = f"Khối {g}"
    cfg = configs_by_grade.get(g, current_config)
    
    code = exam_code.strip()
    if code not in cfg.keys:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy Mã đề {code} trong {g}")
    if len(cfg.keys) <= 1:
        raise HTTPException(status_code=400, detail="Mỗi khối phải giữ lại ít nhất 1 mã đề đáp án")

    del cfg.keys[code]
    save_data_to_disk()
    return {
        "status": "success",
        "message": f"Đã xóa Mã đề {code} khỏi {g}",
        "deleted_code": code,
        "config": cfg
    }

@app.get("/api/results")
def get_all_results(
    exam_code: Optional[str] = None,
    grade: Optional[str] = None,
    class_name: Optional[str] = None
):
    results = list(graded_records.values())
    target_grade = grade.strip() if grade else current_grade
    if target_grade in ["10", "11", "12"]:
        target_grade = f"Khối {target_grade}"
    
    # Lọc theo khối nếu được chỉ định
    if target_grade:
        results = [r for r in results if getattr(r, "grade_level", None) == target_grade or not getattr(r, "grade_level", None)]
    
    cfg = configs_by_grade.get(target_grade, current_config)
    valid_codes = set(cfg.keys.keys())
    
    if exam_code and exam_code.strip():
        req_code = exam_code.strip()
        if req_code in ["INVALID", "SAI_MA_DE"]:
            results = [r for r in results if r.exam_code not in valid_codes]
        else:
            results = [r for r in results if r.exam_code == req_code]

    if class_name and class_name.strip() and class_name.strip() != "ALL":
        req_class = class_name.strip()
        if req_class == "CHUA_RO":
            results = [r for r in results if not r.student_class or not r.student_class.strip()]
        else:
            results = [r for r in results if r.student_class and r.student_class.strip() == req_class]

    return results

@app.put("/api/results/{result_id}")
def update_result_student_info(result_id: str, info: UpdateStudentInfo):
    if result_id not in graded_records:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài thi")
    r = graded_records[result_id]
    if info.student_sbd is not None:
        r.student_sbd = info.student_sbd.strip()
    save_data_to_disk()
    return {"status": "success", "result": r}

@app.delete("/api/results/{result_id}")
def delete_single_result(result_id: str):
    global graded_records
    if result_id in graded_records:
        del graded_records[result_id]
        save_data_to_disk()
        return {"status": "success", "message": f"Đã xóa bài thi {result_id}"}
    raise HTTPException(status_code=404, detail="Không tìm thấy bài thi cần xóa")

@app.post("/api/results/{result_id}/regrade")
def regrade_student_result(result_id: str, new_exam_code: str = Form(...), grade: Optional[str] = Form(None)):
    """
    Chấm lại một bài thi khi giáo viên sửa lại mã đề đúng (rất hữu ích cho các bài Sai mã đề).
    """
    if result_id not in graded_records:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài thi")
    r = graded_records[result_id]
    target_code = new_exam_code.strip()
    
    g_name = grade or getattr(r, "grade_level", None) or current_grade
    if g_name in ["10", "11", "12"]:
        g_name = f"Khối {g_name}"
    active_cfg = configs_by_grade.get(g_name, current_config)

    if target_code not in active_cfg.keys:
        raise HTTPException(status_code=400, detail=f"Mã đề {target_code} chưa được cấu hình đáp án trong {g_name}.")

    raw = r.raw_answers or {}
    p1 = raw.get("p1", {})
    p2 = raw.get("p2", {})
    p3 = raw.get("p3", {})

    regraded = grade_student_exam(
        student_id=r.id,
        file_name=r.file_name,
        detected_sbd=r.student_sbd,
        detected_exam_code=target_code,
        detected_p1=p1,
        detected_p2=p2,
        detected_p3=p3,
        flags={"CHẤM_LẠI": f"Đã đối soát và chuyển sang Mã đề {target_code} ({g_name})"},
        config=active_cfg,
        annotated_image_url=r.annotated_image_url
    )
    regraded.grade_level = g_name
    regraded.name_thumb = r.name_thumb
    regraded.class_thumb = r.class_thumb
    regraded.sbd_thumb = r.sbd_thumb
    regraded.student_name = r.student_name
    regraded.student_class = r.student_class
    regraded.raw_answers = raw
    regraded.raw_answers["corrected_code"] = target_code

    graded_records[result_id] = regraded
    save_data_to_disk()
    return {"status": "success", "result": regraded}

@app.post("/api/grade/upload")
async def upload_and_grade(
    files: List[UploadFile] = File(...),
    force_exam_code: Optional[str] = Form(None),
    grade: Optional[str] = Form(None)
):
    global graded_records
    new_results = []
    
    target_grade = grade.strip() if grade else current_grade
    if target_grade in ["10", "11", "12"]:
        target_grade = f"Khối {target_grade}"
    active_cfg = configs_by_grade.get(target_grade, current_config)

    for f in files:
        contents = await f.read()
        file_id = str(uuid.uuid4())[:8]
        try:
            res, _ = pipeline.process_image_bytes(
                image_bytes=contents,
                file_name=f.filename,
                config=active_cfg,
                student_id=file_id,
                force_exam_code=force_exam_code
            )
            res.grade_level = active_cfg.grade_level
            graded_records[res.id] = res
            new_results.append(res)
        except Exception as e:
            err_res = StudentGradedResult(
                id=file_id,
                file_name=f.filename,
                grade_level=active_cfg.grade_level,
                flagged_issues=[f"Lỗi xử lý ảnh: {str(e)}"]
            )
            graded_records[file_id] = err_res
            new_results.append(err_res)

    save_data_to_disk()
    return {"status": "success", "processed_count": len(new_results), "results": new_results}

@app.post("/api/grade/clear")
def clear_all_results(
    grade: Optional[str] = Query(None),
    exam_code: Optional[str] = Query(None)
):
    global graded_records
    target_grade = grade.strip() if grade else None
    if target_grade in ["10", "11", "12"]:
        target_grade = f"Khối {target_grade}"
    
    cfg = configs_by_grade.get(target_grade or current_grade, current_config)
    valid_codes = set(cfg.keys.keys())

    to_delete = []
    for k, v in list(graded_records.items()):
        v_grade = getattr(v, "grade_level", None)
        if target_grade and v_grade and v_grade != target_grade:
            continue
        
        if exam_code and exam_code.strip() and exam_code.strip() != "ALL":
            req_code = exam_code.strip()
            if req_code in ["INVALID", "SAI_MA_DE"]:
                if v.exam_code in valid_codes:
                    continue
            else:
                if v.exam_code != req_code:
                    continue

        to_delete.append(k)

    for k in to_delete:
        if k in graded_records:
            del graded_records[k]

    save_data_to_disk()
    return {
        "status": "success",
        "message": f"Đã xóa {len(to_delete)} bài thi phù hợp bộ lọc.",
        "deleted_count": len(to_delete)
    }

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
