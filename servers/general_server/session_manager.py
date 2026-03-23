from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from servers.general_server.config import HOST, PORT
from servers.shared.schemas import (
    LiveSessionEndResponse,
    LiveSessionStartRequest,
    LiveSessionStartResponse,
)


LIVE_SESSIONS: dict[str, dict[str, object]] = {}


def build_ws_url(session_id: str) -> str:
    return f"ws://{HOST}:{PORT}/ws/live/{session_id}"


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
        "ended_at": None,
        "total_frames": 0,
        "total_calories": 0.0,
    }

    return LiveSessionStartResponse(
        session_id=session_id,
        user_id=request.user_id,
        status="active",
        started_at=started_at,
        ws_url=build_ws_url(session_id),
        dance_type=request.dance_type,
        content_id=request.content_id,
    )


def get_live_session(session_id: str) -> dict[str, object]:
    session = LIVE_SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def require_active_session(session_id: str) -> dict[str, object]:
    session = get_live_session(session_id)
    if session["status"] != "active":
        raise HTTPException(status_code=400, detail="Session is not active")
    return session


def increment_frame_count(session_id: str) -> dict[str, object]:
    session = require_active_session(session_id)
    session["total_frames"] = int(session["total_frames"]) + 1
    return session


def end_live_session(session_id: str) -> LiveSessionEndResponse:
    session = get_live_session(session_id)
    if session["status"] == "ended":
        raise HTTPException(status_code=400, detail="Session already ended")

    ended_at = datetime.now(timezone.utc)
    session["status"] = "ended"
    session["ended_at"] = ended_at

    return LiveSessionEndResponse(
        session_id=str(session["session_id"]),
        status="ended",
        ended_at=ended_at,
        total_frames=int(session["total_frames"]),
        total_calories=float(session["total_calories"]),
        message="Session ended successfully.",
    )
