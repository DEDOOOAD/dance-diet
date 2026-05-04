from __future__ import annotations

import logging
from datetime import datetime

from fastapi import FastAPI, File, Form, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from servers.general_server.config import APP_NAME, HOST, PORT
from servers.general_server.internal_services import (
    search_classes,
    build_daily_food_intake_payload,
    build_home_payload,
    build_profile_payload,
    create_signup_record,
    delete_user_record,
    login_user,
    process_food_intake_request,
    save_session_data,
    update_user_prototype_record,
    update_user_record,
)
from servers.general_server.session_manager import finish_live_session, start_live_session
from servers.general_server.socket.live_session_route import router as websocket_router
from servers.general_server.socket_manager.ai_outbound import close_ai_connection
from servers.general_server.socket_manager.client_registry import close_client_connection
from servers.shared.schemas import (
    FoodIntakeAnalysisResponse,
    LiveSessionEndRequest,
    LiveSessionEndResponse,
    LiveSessionStartRequest,
    LiveSessionStartResponse,
    UserProfileUpdate,
    UserSignUp,
)


APP_LOGGER = logging.getLogger("uvicorn.error.general_server")

app = FastAPI(title="General REST API", version="1.0.0", description="App-facing REST API for the React Native client.",)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"],)
app.include_router(websocket_router)


@app.on_event("startup")
async def log_server_startup() -> None:
    APP_LOGGER.info("General server startup complete host=%s port=%s app_name=%s", HOST, PORT, APP_NAME,)


@app.middleware("http")
async def add_private_network_access_headers(request: Request, call_next):
    response = await call_next(request)

    if request.headers.get("access-control-request-private-network") == "true":
        response.headers["Access-Control-Allow-Private-Network"] = "true"

    return response


# 회원가입
@app.post("/api/signup")
async def signup(user: UserSignUp):
    return create_signup_record(user)


# 회원 탈퇴
@app.delete("/api/user/{uuid}")
async def delete_user(uuid: str):
    return delete_user_record(uuid)


# 로그인
@app.post("/api/user/{uuid}")
async def login(Email: str, password: str):
    return login_user(Email, password)


# 사용자 프로필 수정. user는 JSON으로 받고 image는 파일로 받습니다.
# 이미지가 없어도 동작하도록 정리할 예정입니다.
@app.put("/api/Profile/{uuid}")
async def update_user(uuid: str, user: UserProfileUpdate, image: UploadFile = File(...)):
    return update_user_record(uuid, user, image)


# 이미지 업로드 확인용 임시 프로필 수정 엔드포인트입니다.
# Swagger에서 먼저 일반 폼 데이터로 테스트한 뒤 정상 동작하면 기존 엔드포인트에 반영합니다.
@app.put("/api/ProfilePrototype/{uuid}")
async def update_user_prototype(uuid: str, name: str | None = Form(None), email: str | None = Form(None), password: str | None = Form(None), age: int | None = Form(None), created_at: datetime | None = Form(None), weight: float | None = Form(None), height: float | None = Form(None), target_weight: float | None = Form(None), target_day: datetime | None = Form(None), today_target_kcal: float | None = Form(None), current_streak: int | None = Form(None), image: UploadFile | None = File(None)):
    form_payload = {"name": name, "email": email, "password": password, "age": age, "created_at": created_at, "weight": weight, "height": height, "target_weight": target_weight, "target_day": target_day, "today_target_kcal": today_target_kcal, "current_streak": current_streak}
    return update_user_prototype_record(uuid, form_payload, image)


# 라이브 세션 시작
@app.post("/api/live/session/start", response_model=LiveSessionStartResponse)
def movements_session_start(payload: LiveSessionStartRequest, http_request: Request) -> LiveSessionStartResponse:
    return start_live_session(payload, http_request)


# 라이브 세션 종료
@app.post("/api/live/session/end", response_model=LiveSessionEndResponse)
async def movements_session_end(request: LiveSessionEndRequest) -> LiveSessionEndResponse:
    response, session = finish_live_session(request.session_id)
    save_session_data(session)
    await close_client_connection(request.session_id, code=1000, reason="Live session ended",)
    await close_ai_connection(request.session_id)
    return response


# 음식 섭취 분석 요청
@app.post("/api/food/intake", response_model=FoodIntakeAnalysisResponse)
async def food_intake_payload(uuid: str = Form(...), day: datetime | None = Form(None), image: UploadFile = File(...)) -> FoodIntakeAnalysisResponse:
    return await process_food_intake_request(uuid, day, image)


# 사용자 프로필 조회
@app.get("/api/profile/{uuid}")
def profile_payload_by_id(uuid: str) -> dict[str, object]:
    return build_profile_payload(uuid)


# 사용자 개인 홈 화면 조회
@app.get("/api/home/{uuid}")
def home_payload(uuid: str) -> dict[str, object]:
    return build_home_payload(uuid)


# 일별 음식 섭취 분석 조회
@app.get("/api/daily_food_intake/{uuid}/")
def daily_food_intake_payload(uuid: str, year: int, month: int, day: int) -> dict[str, object]:
    return build_daily_food_intake_payload(uuid, year, month, day)


@app.get("/api/classes")
def classes_payload(search: str | None = Query(default=None)) -> dict[str, object]:
    return search_classes("춤")

@app.get("/api/classes/search")
def classes_payload(search: str | None = Query(default=None)) -> dict[str, object]: 
    return search_classes(search)
