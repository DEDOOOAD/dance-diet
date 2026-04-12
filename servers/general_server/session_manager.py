from __future__ import annotations

from datetime import datetime, timezone
import logging
from uuid import uuid4

from fastapi import HTTPException, Request

from servers.general_server.config import PORT
from servers.shared.schemas import (
    AiLiveAnalysisMessage,
    LiveFrameResultMessage,
    LiveSessionEndResponse,
    LiveSessionStartRequest,
    LiveSessionStartResponse,
)


LIVE_SESSIONS: dict[str, dict[str, object]] = {}
FRAME_ACTIVITY_GAP_SECONDS = 3.0
RECENT_ACTIVITY_TAIL_SECONDS = 0.5


def build_live_session_ws_url(session_id: str, http_request: Request | None = None) -> str:
    if http_request is None:
        return f"ws://127.0.0.1:{PORT}/ws/live/{session_id}"

    forwarded_proto = (
        http_request.headers.get("x-forwarded-proto") or http_request.url.scheme
    ).split(",")[0].strip()
    forwarded_host = http_request.headers.get("x-forwarded-host")
    host = (
        forwarded_host
        or http_request.headers.get("host")
        or http_request.base_url.netloc
    ).split(",")[0].strip()

    ws_scheme = "wss" if forwarded_proto == "https" else "ws"
    ws_url = f"{ws_scheme}://{host}/ws/live/{session_id}"
    logging.info(ws_url)
    
    return ws_url


def start_live_session(request: LiveSessionStartRequest, http_request: Request | None = None) -> LiveSessionStartResponse:
    started_at = datetime.now(timezone.utc)
    session_id = f"dance_{uuid4()}"

    LIVE_SESSIONS[session_id] = {
        "session_id": session_id,
        "uuid": request.uuid,
        "dance_type": request.dance_type,
        "content_id": request.content_id,
        "status": "active",
        "started_at": started_at,
        "ended_at": None,
        "total_frames": 0,
        "elapsed_seconds": 0.0,
        "total_calories": 0.0,                  # ??遺遺꾩? ?뺤옣?깆쓣 ?꾪빐 ?쇰떒 ?④?
    }

    return LiveSessionStartResponse(
        session_id=session_id,
        uuid=request.uuid,
        status="active",
        started_at=started_at,
        transport="websocket",
        stream_mode="bidirectional",
        dance_type=request.dance_type,
        content_id=request.content_id,
        ws_url=build_live_session_ws_url(session_id, http_request),
    )


def get_live_session_or_raise(session_id: str) -> dict[str, object]:
    session = LIVE_SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def get_active_live_session_or_raise(session_id: str) -> dict[str, object]:
    session = get_live_session_or_raise(session_id)
    if session["status"] != "active":
        raise HTTPException(status_code=400, detail="Session is not active")
    return session


def ensure_active_live_session(session_id: str) -> None:
    get_active_live_session_or_raise(session_id)


def calculate_live_session_elapsed_seconds(session: dict[str, object], reference_time: datetime | None = None) -> float:
    elapsed_seconds = float(session.get("elapsed_seconds", 0.0))
    last_frame_at = session.get("last_frame_at")

    if reference_time is not None and isinstance(last_frame_at, datetime):
        tail_seconds = max(0.0, (reference_time - last_frame_at).total_seconds())
        if tail_seconds <= RECENT_ACTIVITY_TAIL_SECONDS:
            return round(elapsed_seconds + tail_seconds, 1)

    return round(elapsed_seconds, 1)


def update_live_session_frame_progress(session_id: str) -> None:
    # The server owns the running frame counter and elapsed time, so the client
    # does not need to send duplicate totals.
    session = get_active_live_session_or_raise(session_id)
    received_at = datetime.now(timezone.utc)
    last_frame_at = session.get("last_frame_at")

    if isinstance(last_frame_at, datetime):
        frame_gap_seconds = max(0.0, (received_at - last_frame_at).total_seconds())
        if frame_gap_seconds <= FRAME_ACTIVITY_GAP_SECONDS:
            session["elapsed_seconds"] = (
                float(session["elapsed_seconds"]) + frame_gap_seconds
            )

    session["last_frame_at"] = received_at
    session["total_frames"] = int(session["total_frames"]) + 1


def update_live_session_ai_metrics(session_id: str, analysis: AiLiveAnalysisMessage) -> None:
    session = get_active_live_session_or_raise(session_id)
    session["last_ai_processed_at"] = analysis.processed_at
    session["last_calories_burned"] = float(analysis.calories_burned)
    session["last_movement_score"] = float(analysis.movement_score)
    session["total_calories"] = round(
        float(session.get("total_calories", 0.0)) + float(analysis.calories_burned),
        6,
    )


def build_live_frame_result_message(session_id: str, frame_index: int, analysis: AiLiveAnalysisMessage) -> LiveFrameResultMessage:
    session = get_active_live_session_or_raise(session_id)

    # Fields without a reliable measurement stay on the schema defaults.
    return LiveFrameResultMessage(
        session_id=session_id,
        frame_index=frame_index,
        total_frames=int(session["total_frames"]),
        elapsed_seconds=calculate_live_session_elapsed_seconds(session),
        accepted=True,
        calories_burned=float(analysis.calories_burned),
        total_calories=float(session["total_calories"]),
        movement_score=float(analysis.movement_score),
        processed_at=analysis.processed_at,
    )


def finish_live_session(session_id: str) -> LiveSessionEndResponse:
    session = get_live_session_or_raise(session_id)
    if session["status"] == "ended":
        raise HTTPException(status_code=400, detail="Session already ended")

    ended_at = datetime.now(timezone.utc)
    session["status"] = "ended"
    session["ended_at"] = ended_at
    session["elapsed_seconds"] = calculate_live_session_elapsed_seconds(session, ended_at)

    return LiveSessionEndResponse(
        session_id=str(session["session_id"]),
        status="ended",
        ended_at=ended_at,
        total_frames=int(session["total_frames"]),
        elapsed_seconds=float(session["elapsed_seconds"]),
        total_calories=float(session["total_calories"]),
        message="Session ended successfully.",
    )
