from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import UploadFile

from servers.ai_server.services.food_classifier import classify_food_image
from servers.ai_server.services.food_segmenter import run_segmentation_model


BASE_DIR = Path(__file__).resolve().parents[3]
FOOD_DB_PATH = BASE_DIR / "통합 식품영양성분DB.xlsx" # 나중에 식품의약품안전처에서 최신ver로 다운해서 변경 예정
FOOD_NAME_COLUMN = "식품명"
FOOD_CALORIE_COLUMN = "에너지(㎉)"


@lru_cache(maxsize=1)
def load_food_calorie_map() -> dict[str, float]:
    if not FOOD_DB_PATH.exists():
        raise FileNotFoundError(f"칼로리 DB 파일이 없습니다: {FOOD_DB_PATH}")

    df = pd.read_excel(FOOD_DB_PATH)

    if FOOD_NAME_COLUMN not in df.columns:
        raise KeyError(f"칼로리 DB에 '{FOOD_NAME_COLUMN}' 컬럼이 없습니다.")
    if FOOD_CALORIE_COLUMN not in df.columns:
        raise KeyError(f"칼로리 DB에 '{FOOD_CALORIE_COLUMN}' 컬럼이 없습니다.")

    calorie_map: dict[str, float] = {}

    for _, row in df.iterrows():
        raw_name = row[FOOD_NAME_COLUMN]
        raw_calorie = row[FOOD_CALORIE_COLUMN]

        if pd.isna(raw_name) or pd.isna(raw_calorie):
            continue

        name = str(raw_name).strip().lower()
        if not name:
            continue

        calorie_map[name] = float(raw_calorie)

    return calorie_map

def lookup_calories(label: str) -> float:
    calorie_map = load_food_calorie_map()
    return float(calorie_map.get(label.strip().lower(), 0.0))

def build_food_result(classified: dict[str, Any], calories: float) -> dict[str, Any]:
    return {
        "label": classified["label"],
        "calories": calories,
        "confidence": classified["confidence"],
    }

def assemble_foods(segments: list[dict[str, Any]]) -> dict[str, Any]:
    foods: list[dict[str, Any]] = []

    for segment in segments:
        classified = classify_food_image(segment["jpg_bytes"])
        calories = lookup_calories(classified["label"])
        foods.append(build_food_result(classified, calories))

    return {"foods": foods}

async def analyze_food_pipeline(uid: str, jpg_bytes: bytes) -> dict[str, Any]:
    segments = run_segmentation_model(jpg_bytes)
    result = assemble_foods(segments)
    result["uid"] = uid
    return result