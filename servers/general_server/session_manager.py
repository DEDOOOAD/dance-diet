from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, Request

from servers.general_server.config import PORT
from servers.shared.schemas import (
    LiveSessionEndResponse,
    LiveSessionStartRequest,
    LiveSessionStartResponse,
)


LIVE_SESSIONS: dict[str, dict[str, object]] = {}
FRAME_ACTIVITY_GAP_SECONDS = 3.0
RECENT_ACTIVITY_TAIL_SECONDS = 0.5


def build_ws_url(session_id: str, http_request: Request | None = None) -> str:
    if http_request is None:
        return f"ws://127.0.0.1:{PORT}/ws/live/{session_id}"

    forwarded_proto = (http_request.headers.get("x-forwarded-proto") or http_request.url.scheme).split(",")[0].strip()
    forwarded_host = http_request.headers.get("x-forwarded-host")
    host = (forwarded_host or http_request.headers.get("host") or http_request.base_url.netloc).split(",")[0].strip()
    ws_scheme = "wss" if forwarded_proto == "https" else "ws"
    return f"{ws_scheme}://{host}/ws/live/{session_id}"


def create_live_session(
    request: LiveSessionStartRequest,
    http_request: Request | None = None,
) -> LiveSessionStartResponse:
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
        "elapsed_seconds": 0.0,
        "last_frame_at": None,
        "total_calories": 0.0,
    }

    print(f"Created live session: {session_id} for user: {request.user_id}")

    return LiveSessionStartResponse(
        session_id=session_id,
        user_id=request.user_id,
        status="active",
        started_at=started_at,
        ws_url=build_ws_url(session_id, http_request),
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


def calculate_dance_elapsed_seconds(
    session: dict[str, object],
    reference_time: datetime | None = None,
) -> float:
    elapsed_seconds = float(session.get("elapsed_seconds", 0.0))
    last_frame_at = session.get("last_frame_at")

    if reference_time is not None and isinstance(last_frame_at, datetime):
        tail_seconds = max(0.0, (reference_time - last_frame_at).total_seconds())
        if tail_seconds <= RECENT_ACTIVITY_TAIL_SECONDS:
            return round(elapsed_seconds + tail_seconds, 1)

    return round(elapsed_seconds, 1)


def record_live_session_frame(session_id: str) -> dict[str, object]:
    session = require_active_session(session_id)
    received_at = datetime.now(timezone.utc)
    last_frame_at = session.get("last_frame_at")

    if isinstance(last_frame_at, datetime):
        frame_gap_seconds = max(0.0, (received_at - last_frame_at).total_seconds())
        if frame_gap_seconds <= FRAME_ACTIVITY_GAP_SECONDS:
            session["elapsed_seconds"] = float(session["elapsed_seconds"]) + frame_gap_seconds

    session["last_frame_at"] = received_at
    session["total_frames"] = int(session["total_frames"]) + 1
    return session


def end_live_session(session_id: str) -> LiveSessionEndResponse:
    session = get_live_session(session_id)
    if session["status"] == "ended":
        raise HTTPException(status_code=400, detail="Session already ended")

    ended_at = datetime.now(timezone.utc)
    session["status"] = "ended"
    session["ended_at"] = ended_at
    session["elapsed_seconds"] = calculate_dance_elapsed_seconds(session, ended_at)

    return LiveSessionEndResponse(
        session_id=str(session["session_id"]),
        status="ended",
        ended_at=ended_at,
        total_frames=int(session["total_frames"]),
        elapsed_seconds=float(session["elapsed_seconds"]),
        total_calories=float(session["total_calories"]),
        message="Session ended successfully.",
    )
