from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query

from servers.general_server.config import AI_HOST, AI_PORT, APP_NAME
from servers.general_server.mock_data import clone_state
from servers.shared.schemas import (
    GeneralAiProxyResponse,
    LiveSessionEndRequest,
    LiveSessionEndResponse,
    LiveSessionStartRequest,
    LiveSessionStartResponse,
    ServerInfo,
    ToggleUpdateRequest,
    ToggleUpdateResponse,
)


STATE = clone_state()
LIVE_SESSIONS: dict[str, dict[str, object]] = {}

app = FastAPI(
    title="General REST API",
    version="1.0.0",
    description="App-facing REST API for the React Native client.",
)


def build_home_payload() -> dict[str, object]:
    user = STATE["user"]
    return {
        "user": user,
        "streak": STATE["streak"],
        "weekly_days": STATE["weekly_days"],
        "today_summary": {
            "kcal_burned": 1250,
            "kcal_goal": user["daily_kcal_goal"],
            "active_minutes": 45,
            "active_minutes_goal": 80,
            "sessions_completed": 3,
            "session_goal": 4,
        },
        "missions": STATE["missions"],
    }


def build_classes_payload(genre: str | None, search: str | None) -> dict[str, object]:
    classes = deepcopy(STATE["classes"])
    if genre and genre not in {"전체", "all"}:
        classes = [item for item in classes if item["genre"].lower() == genre.lower()]
    if search:
        needle = search.lower()
        classes = [item for item in classes if needle in item["name"].lower() or needle in item["instructor"].lower()]
    genres = ["전체"] + sorted({item["genre"] for item in STATE["classes"]})
    return {
        "genres": genres,
        "active_genre": genre or "전체",
        "search": search or "",
        "count": len(classes),
        "items": classes,
    }


def build_records_payload(period: str) -> dict[str, object]:
    selected = "monthly" if period == "monthly" else "weekly"
    record_state = STATE["records"]
    return {
        "period": selected,
        "stats": record_state[selected]["stats"],
        "chart": record_state[selected]["chart"],
        "history": record_state["history"],
    }


def build_profile_payload() -> dict[str, object]:
    history = STATE["records"]["history"]
    return {
        "user": STATE["user"],
        "summary": {
            "total_kcal": sum(item["kcal"] for item in history),
            "total_sessions": len(history),
            "current_streak_days": STATE["streak"]["current_days"],
        },
        "achievements": STATE["achievements"],
        "settings": STATE["settings"],
    }



def create_live_session(request: LiveSessionStartRequest) -> LiveSessionStartResponse:
    started_at = datetime.now(timezone.utc)
    session_id = f"dance_{uuid4()}"
    LIVE_SESSIONS[session_id] = {
        "session_id": session_id,
        "user_id": request.user_id,
        "dance_type": request.dance_type,      
        "content_id": request.content_id,
        "status": "active",
        "started_at": started_at,
        "ended_at": None,       # 진짜 끝났는지 확인해야해서 넣음
    }
    return LiveSessionStartResponse(
        session_id=session_id,
        user_id=request.user_id,
        status="active",
        started_at=started_at,
        dance_type=request.dance_type,          # 이건 필요한지 아닌지 모르겠지만 일단 넣어봄
        content_id=request.content_id,          # 이것도 마찬가지
    )

def end_session(session):
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["status"] == "ended":
        raise HTTPException(status_code=400, detail="Session already ended")

    ended_at = datetime.now(timezone.utc)
    session["status"] = "ended"
    session["ended_at"] = ended_at
    return ended_at


@app.get("/health", response_model=ServerInfo)
def health() -> ServerInfo:
    return ServerInfo(name=APP_NAME, role="general-server")


@app.get("/ai", response_model=GeneralAiProxyResponse)
def ai_server_info() -> GeneralAiProxyResponse:
    ai_server_url = f"http://{AI_HOST}:{AI_PORT}"
    return GeneralAiProxyResponse(
        ai_server_url=ai_server_url,
        recommended_endpoints=[f"{ai_server_url}/health", f"{ai_server_url}/analyze/pose", f"{ai_server_url}/analyze/gif"],
        note="General server focuses on app APIs and can delegate analysis to the AI server.",
    )


@app.get("/api/app")
def app_metadata() -> dict[str, object]:
    return {
        "app_name": APP_NAME,
        "tabs": [
            {"key": "home", "label": "홈"},
            {"key": "classes", "label": "클래스"},
            {"key": "record", "label": "기록"},
            {"key": "profile", "label": "프로필"},
        ],
        "endpoints": {
            "home": "/api/home",
            "classes": "/api/classes",
            "records": "/api/records?period=weekly",
            "profile": "/api/profile",
            "settings": "/api/settings",
            "achievements": "/api/achievements",
            "live_session_start": "/api/live/session/start",
            "live_session_end": "/api/live/session/end",
        },
    }


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
def records_payload(period: str = Query(default="weekly", pattern="^(weekly|monthly)$")) -> dict[str, object]:
    return build_records_payload(period)


@app.get("/api/profile")
def profile_payload() -> dict[str, object]:
    return build_profile_payload()


@app.get("/api/settings")
def settings_payload() -> dict[str, object]:
    return deepcopy(STATE["settings"])


@app.get("/api/achievements")
def achievements_payload() -> dict[str, object]:
    return {"items": deepcopy(STATE["achievements"])}


@app.post("/api/live/session/start", response_model=LiveSessionStartResponse)
def movements_session_start(request: LiveSessionStartRequest) -> LiveSessionStartResponse:
    return create_live_session(request)



@app.post("/api/live/session/end", response_model=LiveSessionEndResponse)
def movements_session_end(request: LiveSessionEndRequest) -> LiveSessionEndResponse:
    session = LIVE_SESSIONS.get(request.session_id)
    ended_at = end_session(session)

    return LiveSessionEndResponse(
        session_id=str(session["session_id"]),
        status="ended",
        ended_at=ended_at,
        message="Session ended successfully.",
    )


@app.post("/api/settings/toggles", response_model=ToggleUpdateResponse)
def update_toggle(request: ToggleUpdateRequest) -> ToggleUpdateResponse:
    toggles = STATE["settings"]["toggles"]
    if request.key not in toggles:
        raise HTTPException(status_code=400, detail="Unknown toggle key")
    toggles[request.key] = request.value
    return ToggleUpdateResponse(message="Toggle updated", toggles=deepcopy(toggles))
