from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, Path, Request
from fastapi.middleware.cors import CORSMiddleware

from servers.general_server.config import AI_HOST, AI_PORT, APP_NAME, HOST, PORT
from servers.general_server.grpc_runtime_routes import router as grpc_runtime_router
from servers.general_server.session_manager import create_live_session, end_live_session
from servers.shared import db_connect
from servers.shared.Bucket import PROFILE_BUCKET
from servers.shared.schemas import (
    FoodIntakeAnalysisResponse,
    LiveSessionEndRequest,
    LiveSessionEndResponse,
    LiveSessionStartRequest,
    LiveSessionStartResponse,
    UserProfileUpdate,
    UserSignUp,
)

db = db_connect.db_connect()
APP_LOGGER = logging.getLogger("uvicorn.error.general_server")

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

app.include_router(grpc_runtime_router)


SYNCED_SIGNUP_COLUMNS = {"Name", "Email", "Password", "Age"}
SYNCED_PROFILE_COLUMNS = {"Height", "Weight", "Target_weight", "created_at", "Target_day", "Today_Target_kcal", "Current_streak", "Bucket_Profile_Photo", "FilePath"}


@app.on_event("startup")
async def log_server_startup() -> None:
    APP_LOGGER.info(
        "General server startup complete host=%s port=%s app_name=%s",
        HOST,
        PORT,
        APP_NAME,
    )


@app.middleware("http")
async def add_private_network_access_headers(request: Request, call_next):
    response = await call_next(request)

    if request.headers.get("access-control-request-private-network") == "true":
        response.headers["Access-Control-Allow-Private-Network"] = "true"

    return response


def _build_storage_public_url(bucket: str | None, path: str | None) -> str | None:
    if not bucket or not path:
        return None

    return db.storage.from_(bucket).get_public_url(path)


def _raise_upstream_error(error: Exception) -> None:
    message = str(error)
    if "PGRST002" in message or "Error 521" in message or "Web server is down" in message:
        raise HTTPException(
            status_code=503,
            detail="Supabase is temporarily unavailable. Please try again later.",
        )

    raise HTTPException(status_code=500, detail=message)


def _get_profile_record(user_id: str) -> dict[str, Any]:
    try:
        result = (
            db.table("Profile")
            .select("*, signup:SignUp(Name, Email, Age, Password, Created_at)")
            .eq("UUID", user_id)
            .limit(1)
            .execute()
            .data
        )
    except Exception as e:
        _raise_upstream_error(e)

    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")

    record = result[0]
    signup_record = record.pop("signup", None)

    if isinstance(signup_record, list):
        signup_record = signup_record[0] if signup_record else None

    if isinstance(signup_record, dict):
        record["Name"] = signup_record.get("Name")
        record["Email"] = signup_record.get("Email")
        record["Age"] = signup_record.get("Age")
        record["Password"] = signup_record.get("Password")
        record["Created_at"] = signup_record.get("Created_at")

    return record

def get_food_record(user_id: str, day: str) -> dict[str, Any]:
    try:
        rows = (
            db.table("FoodIntake")
            .select("UUID, Day, FoodName, Calories")
            .eq("UUID", user_id)
            .eq("Day", day)
            .execute()
            .data
        )
    except Exception as e:
        _raise_upstream_error(e)

    if not rows:
        return {
            "UUID": user_id,
            "Day": day,
            "Foods": [],
            "TotalCalories": 0.0,
            "RecordCount": 0,
        }

    foods: list[dict[str, Any]] = []
    total_calories = 0.0

    for row in rows:
        try:
            calories = float(row.get("Calories") or 0.0)
        except (TypeError, ValueError):
            calories = 0.0

        normalized_row = dict(row)
        normalized_row["Calories"] = calories
        foods.append(normalized_row)
        total_calories += calories

    return {
        "UUID": user_id,
        "Day": day,
        "Foods": foods,
        "TotalCalories": round(total_calories, 1),
        "RecordCount": len(foods),
    }

# 하루 목표 소모 칼로리 계산
def calculate_daily_target_kcal(
    current_weight: float | None,
    target_weight: float | None,
    target_day: datetime | str | None,
    *,
    reference_date: datetime | None = None,
    kcal_per_kg: float = 7700.0,                    # 1kg을 감량하는데에 필요한 칼로리 근사치
    maximum_daily_kcal: float = 1500.0,             # 목표 달성까지 하루에 감량해야하는 비정상 목표치를 억제(최대 1200까지)
) -> float:
    if current_weight is None or target_weight is None or target_day is None:
        return 0.0

    try:
        current_weight_value = float(current_weight)
        target_weight_value = float(target_weight)
    except (TypeError, ValueError):
        return 0.0

    if isinstance(target_day, str):
        try:
            target_day = datetime.fromisoformat(target_day)
        except ValueError:
            return 0.0

    if not isinstance(target_day, datetime):
        return 0.0

    weight_gap = current_weight_value - target_weight_value
    if weight_gap <= 0:
        return 0.0

    reference = reference_date or datetime.now(tz=target_day.tzinfo)
    days_remaining = max(1, (target_day.date() - reference.date()).days)
    required_kcal = (weight_gap * kcal_per_kg) / days_remaining

    return round(min(required_kcal, maximum_daily_kcal), 1)

# 하루 섭취 칼로리 총합 계산            db에서 가져와서 계산하는 걸로 바꿔야함*****************************************************************
def calculate_total_intake_calories(
    foods: list[dict[str, Any]] | None = None,
    *,
    user_id: str | None = None,
    day: str | None = None,
) -> float:
    if user_id is not None and day is not None:
        response = get_food_record(user_id, day)
        foods = response.get("Foods", [])

    if not foods:
        return 0.0

    total_calories = 0.0

    for food in foods:
        raw_calories = food.get("Calories")
        if raw_calories is None:
            raw_calories = food.get("calories", 0.0)

        try:
            total_calories += float(raw_calories or 0.0)
        except (TypeError, ValueError):
            continue

    return round(total_calories, 1)


# 이 부분은 테스트를 위해서 임시로 임식 데이터를 넣은거고 ai server에서 분석 받는 걸로 리턴하도록 검토 예정
def build_mock_food_intake_analysis(filename: str | None = None) -> dict[str, object]:
    mock_foods = [
        {"label": "bibimbap", "calories": 560.0, "confidence": 0.97},
        {"label": "kimchi", "calories": 35.0, "confidence": 0.99},
        {"label": "fried_egg", "calories": 90.0, "confidence": 0.95},
    ]

    return {
        "foods": mock_foods,
        "total_calories": calculate_total_intake_calories(mock_foods),
        "image_filename": filename,
        "source": "mock-general-server",
        "analyzed_at": datetime.now(),
        "note": "Mock response. Replace this with the AI server food analysis result later.",
    }


async def analyze_food_intake_mock(image: UploadFile) -> dict[str, object]:
    await image.read()
    return build_mock_food_intake_analysis(image.filename)


# 이건 사용자가 프로필 설정에서 세부 목표를 입력 했을때 사용함
def build_home_payload(user_id: str) -> dict[str, object]:
    user_profile = _get_profile_record(user_id)
    today = datetime.now().date().isoformat()

    daily_target_burn_kcal = calculate_daily_target_kcal(
        user_profile.get("Weight"),
        user_profile.get("Target_weight"),
        user_profile.get("Target_day"),
    )
    daily_intake_kcal = calculate_total_intake_calories(user_id=user_id, day=today)

    return {
        "uuid": user_id,
        "day": today,
        "daily_target_burn_kcal": daily_target_burn_kcal,
        "today_target_kcal": daily_target_burn_kcal,
        "target_kcal": daily_target_burn_kcal,
        "daily_intake_kcal": daily_intake_kcal,
        "today_intake_kcal": daily_intake_kcal,
        "intake_kcal": daily_intake_kcal,
        "current_streak": user_profile.get("Current_streak"),
    }

# 이건 서버가 대충 넣어둬야하는 부분
def build_classes_payload(genre: str | None, search: str | None) -> dict[str, object]:
    return True

# 기록이 있어야하는지 모르겠는데 아마 지우지 않을까하는 함수
def build_records_payload(period: str) -> dict[str, object]:
    return True


# 수정 끝
def build_profile_payload(user_id: str) -> dict[str, object]:
    user_profile = _get_profile_record(user_id)
    profile_image_url = _build_storage_public_url(
        user_profile.get("Bucket_Profile_Photo"),
        user_profile.get("FilePath"),
    )
        
    return {
        "uuid": user_profile["UUID"],
        "name": user_profile["Name"],
        "email": user_profile["Email"],
        "age": user_profile["Age"],
        "password": user_profile["Password"],
        "created_at": user_profile["Created_at"],
        "height": user_profile["Height"],
        "weight": user_profile["Weight"],
        "target_weight": user_profile["Target_weight"],
        "target_day": user_profile["Target_day"],
        "target_kcal": user_profile["Today_Target_kcal"],
        "today_target_kcal": user_profile["Today_Target_kcal"],
        "bucket_profile_photo": user_profile["Bucket_Profile_Photo"],
        "filepath": user_profile["FilePath"],
        "profile_image_url": profile_image_url,
        "current_streak": user_profile["Current_streak"],
    }


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
            "update_user": "/api/users_profile/{user_id}",
            "home": "/api/home/{user_id}",
            "classes": "/api/classes",
            "records": "/api/records?period=weekly",
            "profile": "/api/profile?user_id={user_id}",
            "profile_by_path": "/api/profile/{user_id}",
            "food_intake_analysis": "/api/food/intake",
            "settings": "/api/settings",
            "achievements": "/api/achievements",
            "live_session_start": "/api/live/session/start",
            "live_session_end": "/api/live/session/end",
            "live_session_stream": "Use POST /api/live/session/start response.grpc_target and response.stream_method",
        },
    }


@app.post("/api/signup")
async def signup(user: UserSignUp):
    user_id = str(uuid4())
    signup_data = {
        "UUID": user_id,
        "Name": user.name,
        "Email": user.email,
        "Password": user.password,
        "Age": user.age,
        "Created_at": datetime.now().isoformat(),
    }

    try:
        response = db.table("SignUp").insert(signup_data).execute()
        if not response:
            raise HTTPException(status_code=500, detail="Failed to create user")

        return user_id
    except HTTPException:
        return False
    except Exception as e:
        _raise_upstream_error(e)


@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str):
    try:
        profile_response = db.table("Profile").delete().eq("UUID", user_id).execute()

        if not profile_response.data:
            raise HTTPException(status_code=404, detail="User not found")

        return True
    except HTTPException:
        return False
    except Exception as e:
        _raise_upstream_error(e)

def _build_profile_update_data(user: UserProfileUpdate) -> dict[str, Any]:
    payload = user.model_dump(mode="json", exclude_none=True)
    field_map = {
        "name": "Name",
        "email": "Email",
        "password": "Password",
        "age": "Age",
        "created_at": "Created_at",
        "height": "Height",
        "weight": "Weight",
        "target_weight": "Target_weight",
        "target_day": "Target_day",
        "today_target_kcal": "Today_Target_kcal",
        "current_streak": "Current_streak",
        "bucket_profile_photo": "Bucket_Profile_Photo",
        "filepath": "FilePath",
    }
    return {field_map[key]: value for key, value in payload.items()}

def Update_Profile_Image(user_id, image):
    try:
        allowed_types = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]
        ext = Path(image.filename).suffix.lower()
        if ext not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type")

        path = f"{user_id}/{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        image.file.seek(0)
        response = db.storage.from_(PROFILE_BUCKET).upload(path=path, file=image.file,
                file_options={"cache-control": "3600","upsert": "false",},)
        logging.info('Upload response:', response)
    except Exception as e:
        logging.error('Error uploading profile image:', e)
        raise HTTPException(status_code=500, detail="Failed to upload profile image")

# 이거 user는 json인데 image는 다른 형태로 받아서 이거 확인하고 써야함
# 이미지 빼고는 정상작동 중
@app.put("/api/Profile/{user_id}")
async def update_user(user_id: str, user: UserProfileUpdate, image: UploadFile = File(...)):
    try:
        update_data = _build_profile_update_data(user)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
               
        Update_Profile_Image(user_id, image)

        update_signup = {}
        for key in SYNCED_SIGNUP_COLUMNS:
            if key in update_data:
                update_signup[key] = update_data[key]

        update_profile = {}
        for key in SYNCED_PROFILE_COLUMNS:
            if key in update_data:
                update_profile[key] = update_data[key]

        response_signup = None
        if update_signup:
            response_signup = db.table("SignUp").update(update_signup).eq("UUID", user_id).execute()

        response_pro = None
        if update_profile:
            response_pro = db.table("Profile").update(update_profile).eq("UUID", user_id).execute()

        signup_rows = response_signup.data if response_signup else []
        profile_rows = response_pro.data if response_pro else []

        if not signup_rows and not profile_rows:
            raise HTTPException(status_code=404, detail="Profile not found")

        return True
     
    except HTTPException:
        return False
    except Exception as e:
        _raise_upstream_error(e)


# 이 부분은 현재 이미지 업로드를 확인하기 위해 만든 임시 put임 
# swagger 안쓰면 일단 일반형 쓰고 안되면 이거 변형해서 사용
@app.put("/api/ProfilePrototype/{user_id}")
async def update_user_prototype(
    user_id: str,
    name: str | None = Form(None),
    email: str | None = Form(None),
    password: str | None = Form(None),
    age: int | None = Form(None),
    created_at: datetime | None = Form(None),
    weight: float | None = Form(None),
    height: float | None = Form(None),
    target_weight: float | None = Form(None),
    target_day: datetime | None = Form(None),
    today_target_kcal: float | None = Form(None),
    current_streak: int | None = Form(None),
    image: UploadFile | None = File(None),
):
    try:
        form_payload = {
            "name": name,
            "email": email,
            "password": password,
            "age": age,
            "created_at": created_at,
            "weight": weight,
            "height": height,
            "target_weight": target_weight,
            "target_day": target_day,
            "today_target_kcal": today_target_kcal,
            "current_streak": current_streak,
        }
        prototype_field_map = {
            "name": "Name",
            "email": "Email",
            "password": "Password",
            "age": "Age",
            "created_at": "Created_at",
            "height": "Height",
            "weight": "Weight",
            "target_weight": "Target_weight",
            "target_day": "Target_day",
            "today_target_kcal": "Today_Target_kcal",
            "current_streak": "Current_streak",
        }
        # update_data = {
        #     prototype_field_map[key]: value
        #     for key, value in form_payload.items()
        #     if value is not None
        # }
        update_data = {
            prototype_field_map[key]: value.isoformat() if isinstance(value, datetime) else value
            for key, value in form_payload.items()
            if value is not None
        }

        uploaded_path = None
        if image is not None:
            filename = image.filename or ""
            ext = f".{filename.rsplit('.', 1)[-1].lower()}" if "." in filename else ""
            allowed_types = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
            if ext not in allowed_types:
                raise HTTPException(status_code=400, detail="Invalid file type")

            uploaded_path = f"{user_id}/{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            image.file.seek(0)
            contents = image.file.read()
            db.storage.from_(PROFILE_BUCKET).upload(
                path=uploaded_path,
                file=contents,
                file_options={
                    "cache-control": "3600",
                    "upsert": "false",
                    "content-type": image.content_type or "application/octet-stream",
                },
            )
            update_data["Bucket_Profile_Photo"] = PROFILE_BUCKET
            update_data["FilePath"] = uploaded_path

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_signup = {}
        for key in SYNCED_SIGNUP_COLUMNS:
            if key in update_data:
                update_signup[key] = update_data[key]

        update_profile = {}
        for key in SYNCED_PROFILE_COLUMNS:
            if key in update_data:
                update_profile[key] = update_data[key]

        response_signup = None
        if update_signup:
            response_signup = db.table("SignUp").update(update_signup).eq("UUID", user_id).execute()

        response_pro = None
        if update_profile:
            response_pro = db.table("Profile").update(update_profile).eq("UUID", user_id).execute()

        signup_rows = response_signup.data if response_signup else []
        profile_rows = response_pro.data if response_pro else []

        if not signup_rows and not profile_rows:
            raise HTTPException(status_code=404, detail="Profile not found")

        return {
            "ok": True,
            "uploaded_path": uploaded_path,
            "profile_image_url": _build_storage_public_url(PROFILE_BUCKET, uploaded_path) if uploaded_path else None,
        }

    except HTTPException:
        return False
    except Exception as e:
        _raise_upstream_error(e)

@app.post("/api/live/session/start", response_model=LiveSessionStartResponse)
def movements_session_start(
    payload: LiveSessionStartRequest,
    http_request: Request,
) -> LiveSessionStartResponse:
    return create_live_session(payload, http_request)


@app.post("/api/live/session/end", response_model=LiveSessionEndResponse)
def movements_session_end(request: LiveSessionEndRequest) -> LiveSessionEndResponse:
    return end_live_session(request.session_id)


@app.post("/api/food/intake", response_model=FoodIntakeAnalysisResponse)
async def food_intake_payload(image: UploadFile = File(...)) -> FoodIntakeAnalysisResponse:
    payload = await analyze_food_intake_mock(image)
    return FoodIntakeAnalysisResponse(**payload)

@app.get("/api/profile/{user_id}")
def profile_payload_by_id(user_id: str) -> dict[str, object]:
    return build_profile_payload(user_id)

@app.get("/api/home/{user_id}")
def home_payload(user_id: str) -> dict[str, object]:
    return build_home_payload(user_id)


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


# @app.get("/api/settings")
# def settings_payload() -> dict[str, object]:
#     return {}


# @app.get("/api/achievements")
# def achievements_payload() -> dict[str, object]:
#     return {"items": []}


# @app.post("/api/settings/toggles", response_model=ToggleUpdateResponse)
# def update_toggle(request: ToggleUpdateRequest) -> ToggleUpdateResponse:
#     return ToggleUpdateResponse(message="Toggle updated", toggles={request.key: request.value})
