from __future__ import annotations

import os

# HOST = "127.0.0.1"
# PORT = 8000
# DB_HOST = "127.0.0.1" 
# DB_PORT = 7900
# AI_HOST = "127.0.0.1"             # 이 부분은 근이랑 수정 예정
# AI_PORT = 8001
# APP_NAME = "test-for-ai"


# HOST = os.getenv("GENERAL_SERVER_HOST", "0.0.0.0")
HOST = os.getenv("GENERAL_SERVER_HOST", "0.0.0.0")
PORT = int(os.getenv("GENERAL_SERVER_PORT", "8000"))
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "7900"))
AI_HOST = os.getenv("AI_HOST", "0.0.0.0")
AI_PORT = int(os.getenv("AI_PORT", "8002"))
AI_DANCE_WS_PATH = os.getenv("AI_DANCE_LIVE_WS_PATH", "/ws/dance/analyze")
AI_FOOD_WS_PATH = os.getenv("AI_FOOD_WS_PATH", "/ws/food/analyze")

APP_NAME = os.getenv("APP_NAME", "test-for-ai")
