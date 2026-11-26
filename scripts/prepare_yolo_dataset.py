import os
import sys
import glob
import random
import shutil
import cv2
import numpy as np
from pathlib import Path

# Cấu hình đường dẫn
ROOT_DIR = Path(__file_r_).esolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.core.preprocessor import find_scannable_markers
DATASET_DIR = ROOT_DIR / "datasets" / "qm2025_markers"
GK_DIR = Path("D:/Ktra_GK")
SAMPLES_DIR = ROOT_DIR / "samples"

CLASSES = ["marker_tl", "marker_tr", "marker_br", "marker_bl"]

def ensure_dirs():
    for split in ["train", "val"]:
        (DATASET_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (DATASET_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)

def generate_table_background(h, w):
    """Tạo nền bàn gỗ / bàn học ngẫu nhiên."""
    bg_type = random.choice(["wood", "dark_gray", "light_desk", "warm"])
    if bg_type == "wood":
        # Màu gỗ vàng-nâu
        base_color = np.array([random.randint(20, 60), random.randint(40, 90), random.randint(80, 150)], dtype=np.uint8)
        bg = np.full((h, w, 3), base_color, dtype=np.uint8)
        # Tạo vân gỗ
        noise = np.random.randint(-15, 15, (h, w, 3), dtype=np.int16)
        bg = np.clip(bg.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    elif bg_type == "dark_gray":
        val = random.randint(35, 75)
        bg = np.full((h, w, 3), (val, val, val), dtype=np.uint8)
    else:
        val = random.randint(180, 230)
        bg = np.full((h, w, 3), (val - 15, val, val + 10), dtype=np.uint8)
    return bg

def augment_image_and_pts(img, pts):
    """
    Biến đổi phối cảnh ngẫu nhiên (góc chụp nghiêng, xoay nhẹ, đổi nền)
    và ánh xạ chính xác toạ độ 4 mốc góc theo ma trận biến đổi.
    """
    h, w = img.shape[:2]
    
    # 1. Random resize nhẹ
    scale = random.uniform(0.70, 0.90)
    nw, nh = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    scaled_pts = pts * scale

    # 2. Đặt lên nền bàn lớn hơn
    canvas_w = int(nw * random.uniform(1.15, 1.35))
    canvas_h = int(nh * random.uniform(1.15, 1.35))
    bg = generate_table_background(canvas_h, canvas_w)

    # Vị trí ngẫu nhiên trên canvas
    off_x = random.randint(10, canvas_w - nw - 10)
    off_y = random.randint(10, canvas_h - nh - 10)

    # Ghép ảnh vào canvas
    bg[off_y:off_y + nh, off_x:off_x + nw] = resized
    curr_pts = scaled_pts + np.array([off_x, off_y], dtype=np.float32)

    # 3. Biến đổi phối cảnh nhẹ (Góc nghiêng điện thoại)
    src_corners = np.array([
        [0, 0],
        [canvas_w, 0],
        [canvas_w, canvas_h],
        [0, canvas_h]
    ], dtype=np.float32)

    jitter = min(canvas_w, canvas_h) * 0.05
    dst_corners = np.array([
        [random.uniform(0, jitter), random.uniform(0, jitter)],
        [canvas_w - random.uniform(0, jitter), random.uniform(0, jitter)],
        [canvas_w - random.uniform(0, jitter), canvas_h - random.uniform(0, jitter)],
        [random.uniform(0, jitter), canvas_h - random.uniform(0, jitter)]
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(src_corners, dst_corners)
    warped_canvas = cv2.warpPerspective(bg, M, (canvas_w, canvas_h), flags=cv2.INTER_LINEAR, borderValue=(40, 40, 40))

    # Ánh xạ toạ độ 4 marker
    pts_homo = np.hstack([curr_pts, np.ones((4, 1), dtype=np.float32)])
    transformed = (M @ pts_homo.T).T
    warped_pts = transformed[:, :2] / transformed[:, 2:3]

    # 4. Thay đổi độ sáng ngẫu nhiên
    gamma = random.uniform(0.75, 1.25)
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    warped_canvas = cv2.LUT(warped_canvas, table)

    return warped_canvas, warped_pts

def save_sample(image, pts, sample_name, split):
    h, w = image.shape[:2]
    
    # Tính kích thước bounding box chuẩn theo khoảng cách giữa 2 mốc trên
    w_sheet = np.linalg.norm(pts[1] - pts[0])
    box_dim = max(12.0, w_sheet * 0.045) # Đủ bao trọn mốc đen và một ít viền trắng

    lines = []
    for cls_id in range(4):
        cx, cy = pts[cls_id]
        # Bỏ qua nếu mốc bị văng ra ngoài khung hình
        if not (0 <= cx < w and 0 <= cy < h):
            return False
            
        norm_cx = cx / float(w)
        norm_cy = cy / float(h)
        norm_bw = box_dim / float(w)
        norm_bh = box_dim / float(h)
        
        lines.append(f"{cls_id} {norm_cx:.6f} {norm_cy:.6f} {norm_bw:.6f} {norm_bh:.6f}")

    # Ghi ảnh
    img_path = DATASET_DIR / "images" / split / f"{sample_name}.jpg"
    lbl_path = DATASET_DIR / "labels" / split / f"{sample_name}.txt"
    
    cv2.imwrite(str(img_path), image, [cv2.IMWRITE_JPEG_QUALITY, 95])
    with open(lbl_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return True

def main():
    print("=== CHUẨN BỊ DATASET CHO YOLOV8-NANO ĐỊNH VỊ 4 MỐC GÓC ===")
    if DATASET_DIR.exists():
        shutil.rmtree(DATASET_DIR)
    ensure_dirs()

    # Thu thập ảnh gốc
    gk_imgs = list(GK_DIR.rglob("*.jpg"))
    sample_imgs = [
        SAMPLES_DIR / "real_student_1.jpg",
        SAMPLES_DIR / "real_student_2.jpg",
        SAMPLES_DIR / "real_student_3.jpg",
        SAMPLES_DIR / "sample_phone_photo.jpg",
        SAMPLES_DIR / "b7_full.jpg"
    ]
    all_raw = gk_imgs + [p for p in sample_imgs if p.exists()]
    print(f"Tổng số ảnh quét được: {len(all_raw)}")

    valid_samples = []
    for p in all_raw:
        img = cv2.imread(str(p))
        if img is None:
            continue
        pts = find_scannable_markers(img)
        if pts is not None:
            valid_samples.append((img, pts, p.stem))

    print(f"Số ảnh xác thực hợp lệ có đủ 4 mốc: {len(valid_samples)}")

    # Chia train / val ngẫu nhiên (85% train, 15% val)
    random.seed(42)
    random.shuffle(valid_samples)
    val_count = max(10, int(len(valid_samples) * 0.15))
    
    train_pool = valid_samples[val_count:]
    val_pool = valid_samples[:val_count]

    total_train = 0
    total_val = 0

    print("Đang sinh ảnh gốc và tăng cường dữ liệu (Augmentation)...")
    
    # Xử lý tập TRAIN: mỗi ảnh gốc sinh thêm 3 ảnh augmented
    for idx, (img, pts, stem) in enumerate(train_pool):
        # 1. Ảnh gốc
        if save_sample(img, pts, f"train_{idx}_orig_{stem}", "train"):
            total_train += 1
        
        # 2. 3 biến thể augmented (xoay, nghiêng, đặt lên nền bàn gỗ)
        for aug_i in range(3):
            aug_img, aug_pts = augment_image_and_pts(img, pts)
            if save_sample(aug_img, aug_pts, f"train_{idx}_aug{aug_i}_{stem}", "train"):
                total_train += 1

    # Xử lý tập VAL: ảnh gốc + 1 ảnh augmented
    for idx, (img, pts, stem) in enumerate(val_pool):
        if save_sample(img, pts, f"val_{idx}_orig_{stem}", "val"):
            total_val += 1
        aug_img, aug_pts = augment_image_and_pts(img, pts)
        if save_sample(aug_img, aug_pts, f"val_{idx}_aug_{stem}", "val"):
            total_val += 1

    print(f"Sinh thành công dataset:")
    print(f" - Train images: {total_train}")
    print(f" - Val images: {total_val}")

    # Ghi file data.yaml
    data_yaml_content = f"""path: {DATASET_DIR.as_posix()}
train: images/train
val: images/val

nc: 4
names: {CLASSES}
"""
    yaml_path = DATASET_DIR / "data.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(data_yaml_content)

    print(f"Đã tạo file cấu hình: {yaml_path}")
    print("HOÀN THÀNH CHUẨN BỊ DATASET!")

if __name__ == "__main__":
    main()
