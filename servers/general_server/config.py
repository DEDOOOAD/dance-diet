from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _required_env_int(name: str) -> int:
    return int(_required_env(name))

APP_NAME = _required_env("APP_NAME")

HOST = _required_env("GENERAL_SERVER_HOST")
PORT = _required_env_int("GENERAL_SERVER_PORT")

AI_HOST = _required_env("AI_HOST")
AI_PORT = _required_env_int("AI_PORT")
AI_DANCE_WS_PATH = _required_env("AI_DANCE_LIVE_WS_PATH")
AI_FOOD_API_PATH = _required_env("AI_FOOD_API_PATH")

DB_HOST = _required_env("DB_HOST")
DB_PORT = _required_env_int("DB_PORT")

SUPABASE_URL = _required_env("SUPABASE_URL")

SEARCH_URL = _required_env("YOUTUBE_SEARCH_URL")
GET_TAG_URL = _required_env("YOUTUBE_GET_TAG_URL")

PROFILE_BUCKET = _required_env("PROFILE_BUCKET")
FOOD_BUCKET = _required_env("FOOD_BUCKET")
