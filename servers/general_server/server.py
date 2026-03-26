from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from servers.general_server.config import AI_HOST, AI_PORT, APP_NAME
from servers.general_server.session_manager import create_live_session, end_live_session
from servers.general_server.socket_routes import router as websocket_router
from servers.shared import db_connect
from servers.shared.schemas import (
    UserSignUp,
    GeneralAiProxyResponse,
    LiveSessionEndRequest,
    LiveSessionEndResponse,
    LiveSessionStartRequest,
    LiveSessionStartResponse,
    ServerInfo,
    ToggleUpdateRequest,
    ToggleUpdateResponse,
)

db = db_connect.db_connect()

app = FastAPI(
    title="General REST API",
    version="1.0.0",
    description="App-facing REST API for the React Native client.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(websocket_router)

# 수정해야함
def build_home_payload() -> dict[str, object]:
    user_home = db.table("Profile").select("*").execute().data 
    # return {
    #     "user": user,
    #     "streak": STATE["streak"],
    #     "weekly_days": STATE["weekly_days"],
    #     "today_summary": {
    #         "kcal_burned": 1250,
    #         "kcal_goal": user["daily_kcal_goal"],
    #         "active_minutes": 45,
    #         "active_minutes_goal": 80,
    #         "sessions_completed": 3,
    #         "session_goal": 4,
    #     },
    #     "missions": STATE["missions"],
    # }

    return True

# 수정해야함
def build_classes_payload(genre: str | None, search: str | None) -> dict[str, object]:
    # classes = deepcopy(STATE["classes"])
    # if genre and genre != "all":
    #     classes = [item for item in classes if item["genre"].lower() == genre.lower()]
    # if search:
    #     needle = search.lower()
    #     classes = [
    #         item
    #         for item in classes
    #         if needle in item["name"].lower() or needle in item["instructor"].lower()
    #     ]
    # genres = ["all"] + sorted({item["genre"] for item in STATE["classes"]})
    # return {
    #     "genres": genres,
    #     "active_genre": genre or "all",
    #     "search": search or "",
    #     "count": len(classes),
    #     "items": classes,
    # }
    return True

# 수정해야함
def build_records_payload(period: str) -> dict[str, object]:
    # selected = "monthly" if period == "monthly" else "weekly"
    # record_state = STATE["records"]
    # return {
    #     "period": selected,
    #     "stats": record_state[selected]["stats"],
    #     "chart": record_state[selected]["chart"],
    #     "history": record_state["history"],
    # }

    return True


def build_profile_payload(user_id: str) -> dict[str, object]:
    try: 
        user_profile = db.table("Profile").select("*").eq("Mid", user_id).execute().data
        if not user_profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        return {
            "name": user_profile["Name"],
            "email": user_profile["Email"],
            "age": user_profile["Age"],
            "height": user_profile["Height"],
            "weight": user_profile["Weight"],
            "target_kcal": user_profile["target_kcal"],
            "current_streak": user_profile["Current_streak"],
            "created_at": user_profile["created_at"]
        }
    
    finally: return False

@app.get("/api/app")
def app_metadata() -> dict[str, object]:
    return {
        "app_name": APP_NAME,
        "tabs": [
            {"key": "home", "label": "Home"},
            {"key": "classes", "label": "Classes"},
            {"key": "record", "label": "Record"},
            {"key": "profile", "label": "Profile"},
        ],
        "endpoints": {
            "signup": "/api/signup",
            "delete_user": "/api/users/{user_id}",  
            "update_user": "/api/users/{user_id}",
            "home": "/api/home",
            "classes": "/api/classes", 
            "records": "/api/records?period=weekly",
            "profile": "/api/profile",
            "settings": "/api/settings",
            "achievements": "/api/achievements",
            "live_session_start": "/api/live/session/start",
            "live_session_end": "/api/live/session/end",
            "live_session_socket": "/ws/live/{session_id}",
        },
    }

# insert
@app.post("/api/signup")
async def signup(user: UserSignUp):
    try:
        response = db.table("SignUp").insert({
            "Name": user.name,
            "Email": user.email,
            "Password": user.password,
            "Age": user.age,
            "UUID": str(uuid4())
        }).execute()
        
        return {"message": "회원가입 성공", "data": response.data}
        
    except Exception as e:
        # 에러 발생 시 상세 내용 출력
        raise HTTPException(status_code=500, detail=str(e))

# select        # 이걸 어따 쓰지;
@app.get("/api/users")
async def get_users():
    response = db.table("SignUp").select("*").execute()
    return response.data

# delete
@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str):
    try:
        response = db.table("SignUp").delete().eq("Mid", user_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="삭제할 사용자를 찾을 수 없습니다.")

        return {"message": "회원 삭제 성공!", "deleted_user": response.data}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"삭제 중 오류 발생: {str(e)}")

# update
@app.put("/api/users/{user_id}")
async def update_user(user_id: str, user: UserSignUp):
    try:
        update_data = ({
            "Email": user.email,
            "Password": user.password,
            "Age": user.age
        })

        response = db.table("SignUp").update(update_data).eq("Mid", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="업데이트할 사용자를 찾을 수 없습니다.")

        return {
            "message": "이메일, 비밀번호, 나이가 성공적으로 업데이트되었습니다!",
            "data": response.data
        }
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/live/session/start", response_model=LiveSessionStartResponse)
def movements_session_start(request: LiveSessionStartRequest) -> LiveSessionStartResponse:
    return create_live_session(request)


@app.post("/api/live/session/end", response_model=LiveSessionEndResponse)
def movements_session_end(request: LiveSessionEndRequest) -> LiveSessionEndResponse:
    return end_live_session(request.session_id)


@app.get("/health", response_model=ServerInfo)
def health() -> ServerInfo:
    return ServerInfo(name=APP_NAME, role="general-server")


@app.get("/ai", response_model=GeneralAiProxyResponse)
def ai_server_info() -> GeneralAiProxyResponse:
    ai_server_url = f"http://{AI_HOST}:{AI_PORT}"
    return GeneralAiProxyResponse(
        ai_server_url=ai_server_url,
        recommended_endpoints=[
            f"{ai_server_url}/health",
            f"{ai_server_url}/analyze/pose",
            f"{ai_server_url}/analyze/gif",
        ],
        note="General server focuses on app APIs and can delegate analysis to the AI server.",
    )



@app.get("/api/profile")
def profile_payload() -> dict[str, object]:
    return build_profile_payload()

# 수정해야함 아래 전부
@app.get("/api/home")
def home_payload() -> dict[str, object]:
    return build_home_payload()


@app.get("/api/classes")
def classes_payload(
    genre: str | None = Query(default=None),
    search: str | None = Query(default=None),
) -> dict[str, object]:
    return build_classes_payload(genre, search)


@app.get("/api/records")
def records_payload(
    period: str = Query(default="weekly", pattern="^(weekly|monthly)$"),
) -> dict[str, object]:
    return build_records_payload(period)





# 수정해야함

# @app.get("/api/settings")
# def settings_payload() -> dict[str, object]:
#     return deepcopy(STATE["settings"])


# 수정해야함

# @app.get("/api/achievements")
# def achievements_payload() -> dict[str, object]:
#     return {"items": deepcopy(STATE["achievements"])}





# 수정해야함

# @app.post("/api/settings/toggles", response_model=ToggleUpdateResponse)
# def update_toggle(request: ToggleUpdateRequest) -> ToggleUpdateResponse:
#     toggles = STATE["settings"]["toggles"]
#     if request.key not in toggles:
#         raise HTTPException(status_code=400, detail="Unknown toggle key")
#     toggles[request.key] = request.value
#     return ToggleUpdateResponse(
#         message="Toggle updated",
#         toggles=deepcopy(toggles),
#     )
