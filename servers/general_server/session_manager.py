from __future__ import annotations

from fastapi import HTTPException, Request

from servers.general_server.grpc_live_session_runtime import get_runtime
from servers.general_server.grpc_stream_routes import STREAM_METHOD
from servers.general_server.grpc_session_manager import (
    calculate_dance_elapsed_seconds,
    create_live_session as create_grpc_live_session,
    end_live_session as end_grpc_live_session,
    get_live_session,
    record_live_session_frame,
    require_active_session,
)
from servers.shared.schemas import (
    LiveSessionEndResponse,
    LiveSessionStartRequest,
    LiveSessionStartResponse,
)


def create_live_session(
    request: LiveSessionStartRequest,
    http_request: Request | None = None,
) -> LiveSessionStartResponse:
    del http_request

    try:
        runtime = get_runtime()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return create_grpc_live_session(
        request,
        runtime.grpc_target,
        STREAM_METHOD,
    )


def end_live_session(session_id: str) -> LiveSessionEndResponse:
    return end_grpc_live_session(session_id)
