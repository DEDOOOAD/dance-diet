from __future__ import annotations

import os

HOST = os.getenv("GENERAL_SERVER_HOST", "10.101.232.232")
# HOST = os.getenv("GENERAL_SERVER_HOST", "127.0.0.1")
PORT = int(os.getenv("GENERAL_SERVER_PORT", "8000"))
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "7900"))
AI_HOST = os.getenv("AI_HOST", "10.101.233.33")
AI_PORT = int(os.getenv("AI_PORT", "8001"))
AI_DANCE_WS_PATH = os.getenv("AI_DANCE_LIVE_WS_PATH", "/ws/dance/analyze")
AI_FOOD_API_PATH = os.getenv("AI_FOOD_API_PATH", "/api/food/analyze")

APP_NAME = os.getenv("APP_NAME", "test-for-ai")
