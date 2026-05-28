# supabase꺼 프로시저 호출 supabase.rpc("Replace_ALL").execute()

import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def db_connect():
    url = _required_env("SUPABASE_URL")
    credential = _required_env("SUPABASE_SERVICE_ROLE")

    # Supabase 클라이언트 생성
    supabase: Client = create_client(url, credential)

    return supabase
