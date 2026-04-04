from __future__ import annotations

import os


HOST = os.getenv("GENERAL_SERVER_HOST", "0.0.0.0")
PORT = int(os.getenv("GENERAL_SERVER_PORT", "8000"))
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "7900"))
AI_HOST = os.getenv("AI_HOST", "127.0.0.1")
AI_PORT = int(os.getenv("AI_PORT", "8001"))
APP_NAME = os.getenv("APP_NAME", "test-for-ai")
