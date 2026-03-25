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


@lru_cache(maxsize=1)
def load_food_calorie_map() -> dict[str, float]:
    df = pd.read_excel(FOOD_DB_PATH)

    name_column = "식품명"
    calorie_column = "에너지(㎉)"

    calorie_map: dict[str, float] = {}

    for _, row in df.iterrows():
        name = str(row[name_column]).strip()
        calorie = row[calorie_column]

        if not name:
            continue
        if pd.isna(calorie):
            continue

        calorie_map[name.lower()] = float(calorie)

    return calorie_map


def lookup_calories(label: str) -> float:
    calorie_map = load_food_calorie_map()
    return float(calorie_map.get(label.strip().lower(), 0))
