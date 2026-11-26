# 🎯 GradingWeb — Hệ Thống Chấm Thi Trắc Nghiệm Chuẩn QM 2025

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-orange.svg)](https://ultralytics.com)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-green.svg)](https://opencv.org/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

Hệ thống web tự động chấm điểm bài thi trắc nghiệm theo **mẫu phiếu QM 2025** mới nhất của Bộ Giáo dục & Đào tạo. Ứng dụng kết hợp thị giác máy tính (**OpenCV**) và mô hình học sâu (**YOLOv8**) để tự động căn chỉnh góc chụp, nhận dạng Số báo danh, Mã đề thi và chấm điểm chính xác 3 phần thi.

---

## 🚀 Tính năng nổi bật

- **Hỗ trợ đầy đủ 3 phần thi QM 2025:**
  - **Phần I (Nhiều lựa chọn):** 40 câu trắc nghiệm 4 đáp án (A, B, C, D).
  - **Phần II (Đúng/Sai):** 8 câu hỏi với 4 ý a, b, c, d mỗi câu; tính điểm phi tuyến tính chuẩn Bộ GD&ĐT (đúng 1 ý: 0.1đ; 2 ý: 0.25đ; 3 ý: 0.5đ; 4 ý: 1.0đ).
  - **Phần III (Trả lời ngắn):** 6 câu hỏi điền số, hỗ trợ số nguyên, số thập phân và dấu âm/dương.
- **Tự động căn chỉnh & khử nghiêng:** Sử dụng mô hình **YOLOv8** đã qua huấn luyện nhận diện 4 điểm mốc định vị (markers) ở 4 góc phiếu, sau đó áp dụng biến đổi phối cảnh (*Perspective Transform*) nắn thẳng ảnh chụp ngay cả khi chụp xiên hoặc méo.
- **Nhận diện thông tin thí sinh:** Tự động đọc vùng tô **Số báo danh** (6 chữ số) và **Mã đề thi** (3 chữ số).
- **Quản lý đáp án đa năng:**
  - Cấu hình đáp án theo từng khối lớp (Khối 10, Khối 11, Khối 12).
  - Hỗ trợ nhiều mã đề trong cùng một kỳ thi.
  - Gom các bài thi bị tô nhầm mã đề vào mục riêng, cho phép giáo viên sửa mã đề và chấm lại (*Regrade*) tức thì.
- **Giao diện Web trực quan (Single Page App):**
  - Tải lên một hoặc nhiều ảnh cùng lúc (batch processing).
  - Hiển thị ảnh sau chấm với lớp phủ (*overlay*) đánh dấu rõ các câu Đúng (xanh), Sai (đỏ) và câu không làm.
  - Hỗ trợ thiết bị di động truy cập trực tiếp qua cùng mạng WiFi/LAN.
- **Xuất báo cáo điểm:** Xuất toàn bộ kết quả chấm điểm ra file **Excel (.xlsx)** đa sheet chuyên nghiệp.

---

## 🛠️ Công nghệ sử dụng

| Thành phần | Công nghệ / Thư viện |
|------------|-----------------------|
| **Backend** | Python 3.10+, FastAPI, Uvicorn, Pydantic |
| **Computer Vision / AI** | OpenCV, NumPy, Ultralytics YOLOv8 |
| **Frontend** | HTML5, Modern CSS, Vanilla JavaScript (ES6) |
| **Báo cáo & Dữ liệu** | OpenPyXL, JSON Persistence |

---

## 📁 Cấu trúc thư mục

```text
GradingWeb/
├── app/
│   ├── api/
│   │   └── main.py                  # API endpoints FastAPI & router
│   ├── core/
│   │   ├── annotator.py             # Vẽ overlay kết quả lên ảnh bài thi
│   │   ├── bubble_analyzer.py       # Phân tích độ đậm vùng tô ô tròn
│   │   ├── marker_detector.py       # Nhận diện marker bằng YOLOv8
│   │   ├── models.py                # Pydantic models & data classes
│   │   ├── pipeline.py              # Luồng xử lý OMR hoàn chỉnh
│   │   ├── preprocessor.py          # Tiền xử lý ảnh & nắn góc phẳng
│   │   ├── scorer.py                # Logic chấm điểm theo quy chế QM 2025
│   │   └── template_qm2025.py       # Tọa độ hình học chuẩn mẫu QM 2025
│   ├── data/
│   │   ├── config.json              # File cấu hình đáp án
│   │   └── results.json             # Lưu trữ lịch sử kết quả chấm
│   ├── models/
│   │   └── yolov8_qm2025_markers.pt # Model YOLOv8 định vị 4 góc phiếu
│   └── static/
│       ├── index.html               # Giao diện người dùng web
│       └── app.js                   # Logic xử lý giao diện phía client
├── samples/                         # Ảnh bài thi mẫu thực tế kiểm thử
├── scripts/                         # Script trích xuất dataset & train YOLO
├── requirements.txt                 # Danh sách thư viện phụ thuộc
├── run_server.py                    # Script chạy FastAPI server
├── run_web.bat                      # Phím tắt chạy nhanh trên Windows
└── README.md                        # Tài liệu hướng dẫn dự án
```

---

## 💻 Hướng dẫn cài đặt & Khởi chạy

### 1. Yêu cầu hệ thống
- Hệ điều hành: Windows, macOS hoặc Linux.
- Python: Phiên bản **3.10** trở lên.
- Đã cài đặt **Git**.

### 2. Tải mã nguồn về máy
```bash
git clone https://github.com/nhattan0114/GradingWeb.git
cd GradingWeb
```

### 3. Tạo môi trường ảo & cài đặt thư viện
```bash
# Khởi tạo môi trường ảo (tuỳ chọn nhưng khuyến nghị)
python -m venv venv

# Kích hoạt môi trường ảo:
# Trên Windows:
venv\Scripts\activate
# Trên Linux/macOS:
source venv/bin/activate

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

### 4. Khởi chạy ứng dụng
Chạy trực tiếp bằng lệnh Python:
```bash
python run_server.py
```
*Hoặc trên Windows, bạn có thể click đúp chuột vào file `run_web.bat`.*

### 5. Truy cập ứng dụng
- **Trên máy tính:** Mở trình duyệt và truy cập: [http://localhost:8000](http://localhost:8000)
- **Trên điện thoại:** Kết nối điện thoại cùng mạng WiFi với máy tính và truy cập theo địa chỉ IP hiển thị trên màn hình console (ví dụ: `http://192.168.1.x:8000`).

---

## 📄 Bản quyền

Dự án được phân phối dưới giấy phép **MIT License**. Mọi đóng góp và cải tiến đều được hoan nghênh!
