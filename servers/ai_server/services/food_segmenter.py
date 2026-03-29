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

def encode_image_to_jpg_bytes(image: np.ndarray) -> bytes | None:
    if image.size == 0:
        return None

    success, encoded = cv2.imencode(".jpg", image)
    if not success:
        return None

    return encoded.tobytes()

def segment_food(image_path: str) -> list[bytes]:
    model = load_segmenter_model()
    results = model.predict(source=image_path, verbose=False)

    if not results:
        return []

    result = results[0]

    segmented_images: list[bytes] = []

    for segmented_image in result:
        if segmented_image is None:
            continue

        if isinstance(segmented_image, np.ndarray):
            jpg_bytes = encode_image_to_jpg_bytes(segmented_image)
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
