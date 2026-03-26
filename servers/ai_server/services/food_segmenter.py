from __future__ import annotations

import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parents[3]
MODEL1_PATH = BASE_DIR / "servers" / "ai_server" / "models" / "food_segmenter.pt" # 음식 이미지 분할 모델


@lru_cache(maxsize=1)
def load_segmenter_model() -> YOLO:
    if not MODEL1_PATH.exists():
        raise FileNotFoundError(f"음식 이미지 분할 모델 파일이 없습니다: {MODEL1_PATH}")

    return YOLO(str(MODEL1_PATH))

def crop_to_jpg_bytes(image: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> bytes | None:
    height, width = image.shape[:2]

    x1 = max(0, min(x1, width))
    y1 = max(0, min(y1, height))
    x2 = max(0, min(x2, width))
    y2 = max(0, min(y2, height))

    if x2 <= x1 or y2 <= y1:
        return None

    crop = image[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    success, encoded = cv2.imencode(".jpg", crop)
    if not success:
        return None

    return encoded.tobytes()

def segment_food(image_path: str) -> list[bytes]:
    model = load_segmenter_model()
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(f"이미지를 읽을 수 없습니다: {image_path}")

    results = model.predict(source=image_path, verbose=False)
    if not results:
        return []

    result = results[0]
    if result.boxes is None or result.boxes.xyxy is None:
        return []

    segmented_images: list[bytes] = []

    for box in result.boxes.xyxy:
        x1, y1, x2, y2 = map(int, box.tolist())
        jpg_bytes = crop_to_jpg_bytes(image, x1, y1, x2, y2)

        if jpg_bytes is not None:
            segmented_images.append(jpg_bytes)

    return segmented_images

def run_segmentation_model(jpg_bytes: bytes) -> list[dict[str, Any]]:
    temp_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(jpg_bytes)
            temp_path = tmp.name

        segmented_images = segment_food(temp_path)

        return [{"jpg_bytes": image_bytes} for image_bytes in segmented_images]

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
