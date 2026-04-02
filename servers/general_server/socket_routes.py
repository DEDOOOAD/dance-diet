from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from servers.general_server.session_manager import (
    calculate_dance_elapsed_seconds,
    record_live_session_frame,
    require_active_session,
)
from servers.general_server.socket_manager import connect, disconnect


router = APIRouter()


@router.websocket("/ws/live/{session_id}")
async def live_session_socket(websocket: WebSocket, session_id: str) -> None:
    require_active_session(session_id)

    await connect(session_id, websocket)

    try:
        await websocket.send_json(
            {
                "type": "session_ready",
                "session_id": session_id,
                "message": "WebSocket connected",
            }
        )

        while True:
            payload = await websocket.receive_json()
            message_type = payload.get("type", "unknown")

            if message_type == "frame":
                session = record_live_session_frame(session_id)
                await websocket.send_json(
                    {
                        "type": "frame_ack",
                        "session_id": session_id,
                        "frame_index": payload.get("frame_index"),
                        "total_frames": session["total_frames"],
                        "elapsed_seconds": calculate_dance_elapsed_seconds(session),
                        "total_calories": session["total_calories"],
                    }
                )
                continue

            if message_type == "ping":
                await websocket.send_json({"type": "pong", "session_id": session_id})
                continue

            await websocket.send_json(
                {
                    "type": "error",
                    "session_id": session_id,
                    "message": "Unsupported message type",
                }
            )
    except WebSocketDisconnect:
        disconnect(session_id)
