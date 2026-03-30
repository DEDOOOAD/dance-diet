from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, Path
from fastapi.middleware.cors import CORSMiddleware
from uvicorn import logging

from servers.general_server.config import AI_HOST, AI_PORT, APP_NAME
from servers.general_server.session_manager import create_live_session, end_live_session
from servers.general_server.socket_routes import router as websocket_router
from servers.shared import db_connect
from servers.shared.Bucket import PROFILE_BUCKET
from servers.shared.schemas import (
    GeneralAiProxyResponse,
    LiveSessionEndRequest,
    LiveSessionEndResponse,
    LiveSessionStartRequest,
    LiveSessionStartResponse,
    # ServerInfo,
    # ToggleUpdateRequest,        # 이거 두개 수정해야함
    # ToggleUpdateResponse,
    UserProfileUpdate,
    UserSignUp,
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

SYNCED_SIGNUP_COLUMNS = {"Name", "Email", "Password", "Age"}
SYNCED_PROFILE_COLUMNS = {"Height", "Weight", "Target_weight", "created_at", "Target_day", "Today_Target_kcal", "Current_streak", "Bucket_Profile_Photo", "FilePath"}


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



# 수정
def build_home_payload() -> dict[str, object]:
    return True
def build_classes_payload(genre: str | None, search: str | None) -> dict[str, object]:
    return True
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
            "home": "/api/home",
            "classes": "/api/classes",
            "records": "/api/records?period=weekly",
            "profile": "/api/profile?user_id={user_id}",
            "profile_by_path": "/api/profile/{user_id}",
            "settings": "/api/settings",
            "achievements": "/api/achievements",
            "live_session_start": "/api/live/session/start",
            "live_session_end": "/api/live/session/end",
            "live_session_socket": "/ws/live/{session_id}",
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
def movements_session_start(request: LiveSessionStartRequest) -> LiveSessionStartResponse:
    return create_live_session(request)


@app.post("/api/live/session/end", response_model=LiveSessionEndResponse)
def movements_session_end(request: LiveSessionEndRequest) -> LiveSessionEndResponse:
    return end_live_session(request.session_id)


@app.get("/api/profile")
def profile_payload(user_id: str = Query(...)) -> dict[str, object]:
    return build_profile_payload(user_id)


@app.get("/api/profile/{user_id}")
def profile_payload_by_id(user_id: str) -> dict[str, object]:
    return build_profile_payload(user_id)

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


# @app.get("/api/settings")
# def settings_payload() -> dict[str, object]:
#     return {}


# @app.get("/api/achievements")
# def achievements_payload() -> dict[str, object]:
#     return {"items": []}


# @app.post("/api/settings/toggles", response_model=ToggleUpdateResponse)
# def update_toggle(request: ToggleUpdateRequest) -> ToggleUpdateResponse:
#     return ToggleUpdateResponse(message="Toggle updated", toggles={request.key: request.value})
