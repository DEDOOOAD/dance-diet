from __future__ import annotations

import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parents[3]
MODEL2_PATH = BASE_DIR / "servers" / "ai_server" / "models" / "food_classifier.pt" # 음식 판별 모델


@lru_cache(maxsize=1)
def load_classifier_model() -> YOLO:
    if not MODEL2_PATH.exists():
        raise FileNotFoundError(f"음식 판별 모델 파일이 없습니다: {MODEL2_PATH}")

    return YOLO(str(MODEL2_PATH))

def predict_food(image_path: str) -> dict[str, Any]:
    model = load_classifier_model()
    results = model.predict(source=image_path, verbose=False)

    if not results:
        return {
            "label": "unknown",
            "confidence": 0.0,
        }

    result = results[0]
    probs = result.probs

    if probs is None:
        return {
            "label": "unknown",
            "confidence": 0.0,
        }

    top_index = int(probs.top1)
    confidence = float(probs.top1conf.item())
    names = result.names or {}

    label = names.get(top_index, "unknown")

    return {
        "label": str(label),
        "confidence": confidence,
    }

def classify_food_image(jpg_bytes: bytes) -> dict[str, Any]:
    temp_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(jpg_bytes)
            temp_path = tmp.name

        return predict_food(temp_path)

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
