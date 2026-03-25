# supabase꺼 프로시저 호출 supabase.rpc("Replace_ALL").execute()

import os
from dotenv import load_dotenv
from supabase import create_client, Client

def db_connect():
    load_dotenv()
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")

    # Supabase 클라이언트 생성
    supabase: Client = create_client(url, key)
    return supabase