from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from servers.general_server.config import AI_HOST, AI_PORT, APP_NAME
from servers.general_server.session_manager import create_live_session, end_live_session
from servers.general_server.socket_routes import router as websocket_router
from servers.shared import db_connect
from servers.shared.schemas import (
    GeneralAiProxyResponse,
    LiveSessionEndRequest,
    LiveSessionEndResponse,
    LiveSessionStartRequest,
    LiveSessionStartResponse,
    ServerInfo,
    ToggleUpdateRequest,        # 이거 두개 수정해야함
    ToggleUpdateResponse,
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
            .select("*")
            .eq("UUID", user_id)
            .limit(1)
            .execute()
            .data
        )
    except Exception as e:
        _raise_upstream_error(e)

    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")

    return result[0]


def _build_profile_insert_data(user: UserSignUp, user_id: str) -> dict[str, Any]:
    profile_data: dict[str, Any] = {
        "UUID": user_id,
        "Name": user.name,
        "Email": user.email,
        "Password": user.password,
        "Age": user.age,
        "Current_streak": user.current_streak,
        "Created_at": user.created_at.isoformat(),
    }
    optional_fields = {
        "Height": user.height,
        "Weight": user.weight,
        "Target_weight": user.target_weight,
        "Target_day": user.target_day.isoformat() if user.target_day else None,
        "Today_Target_kcal": user.today_target_kcal,
        "Bucket_Profile_Photo": user.bucket_profile_photo,
        "FilePath": user.filepath,
    }
    profile_data.update(
        {column: value for column, value in optional_fields.items() if value is not None}
    )
    return profile_data


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


def _build_signup_update_data(profile_update_data: dict[str, Any]) -> dict[str, Any]:
    return {
        column: value
        for column, value in profile_update_data.items()
        if column in SYNCED_SIGNUP_COLUMNS
    }


def build_home_payload() -> dict[str, object]:
    return True


def build_classes_payload(genre: str | None, search: str | None) -> dict[str, object]:
    return True


def build_records_payload(period: str) -> dict[str, object]:
    return True


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
    profile_data = _build_profile_insert_data(user, user_id)

    try:
        db.table("SignUp").insert(signup_data).execute()

        return {
            "message": "User created successfully",
            "user_id": user_id,
            "profile": build_profile_payload(user_id),
        }
    except HTTPException:
        raise
    except Exception as e:
        _raise_upstream_error(e)


@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str):
    try:
        profile_response = db.table("Profile").delete().eq("UUID", user_id).execute()
        signup_response = db.table("SignUp").delete().eq("UUID", user_id).execute()

        if not profile_response.data and not signup_response.data:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "message": "User deleted successfully",
            "user_id": user_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        _raise_upstream_error(e)


@app.put("/api/users_profile/{user_id}")
@app.patch("/api/users_profile/{user_id}")
@app.put("/api/Profile/{user_id}")
@app.patch("/api/Profile/{user_id}")
async def update_user(user_id: str, user: UserProfileUpdate):
    try:
        update_data = _build_profile_update_data(user)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        response = db.table("Profile").update(update_data).eq("UUID", user_id).execute()

        signup_update_data = _build_signup_update_data(update_data)
        if signup_update_data:
            db.table("SignUp").update(signup_update_data).eq("UUID", user_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")

        return {
            "message": "Profile updated successfully",
            "data": build_profile_payload(user_id),
        }
    except HTTPException:
        raise
    except Exception as e:
        _raise_upstream_error(e)


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
