from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from servers.shared.schemas import (
    LiveSessionEndResponse,
    LiveSessionStartRequest,
    LiveSessionStartResponse,
)


LOGGER = logging.getLogger("uvicorn.error.grpc_live_session")
GRPC_LIVE_SESSIONS: dict[str, dict[str, object]] = {}
FRAME_ACTIVITY_GAP_SECONDS = 3.0
RECENT_ACTIVITY_TAIL_SECONDS = 0.5


def create_live_session(
    request: LiveSessionStartRequest,
    grpc_target: str,
    stream_method: str,
) -> LiveSessionStartResponse:
    started_at = datetime.now(timezone.utc)
    session_id = f"dance_{uuid4()}"

    GRPC_LIVE_SESSIONS[session_id] = {
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

    LOGGER.info(
        "Created gRPC live session %s for user=%s dance_type=%s content_id=%s grpc_target=%s",
        session_id,
        request.user_id,
        request.dance_type,
        request.content_id,
        grpc_target,
    )

    return LiveSessionStartResponse(
        session_id=session_id,
        user_id=request.user_id,
        status="active",
        started_at=started_at,
        grpc_target=grpc_target,
        stream_method=stream_method,
        dance_type=request.dance_type,
        content_id=request.content_id,
    )


def get_live_session(session_id: str) -> dict[str, object]:
    session = GRPC_LIVE_SESSIONS.get(session_id)
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

    LOGGER.info(
        "Ended gRPC live session %s total_frames=%s elapsed_seconds=%s total_calories=%s",
        session_id,
        session["total_frames"],
        session["elapsed_seconds"],
        session["total_calories"],
    )

    return LiveSessionEndResponse(
        session_id=str(session["session_id"]),
        status="ended",
        ended_at=ended_at,
        total_frames=int(session["total_frames"]),
        elapsed_seconds=float(session["elapsed_seconds"]),
        total_calories=float(session["total_calories"]),
        message="Session ended successfully.",
    )
