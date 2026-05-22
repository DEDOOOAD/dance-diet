from __future__ import annotations

import base64
import json

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from websockets.exceptions import ConnectionClosed, InvalidStatus

from servers.general_server.session_manager import (
    build_live_frame_result_message,
    ensure_active_live_session,
    update_live_session_ai_metrics,
    update_live_session_frame_progress,
)
from servers.general_server.socket_manager.ai_outbound import (
    analyze_frame_with_ai,
    initialize_ai_bridge,
    ping_for_ai_server_connection,
)
from servers.general_server.socket_manager.client_registry import (
    accept_client_connection,
    remove_client_connection,
)
from servers.shared.schemas import LiveFrameMessage, LiveFrameMessage_go_ai_server

router = APIRouter()


async def send_socket_error(websocket: WebSocket, session_id: str, message: str) -> None:
    await websocket.send_json({"type": "error", "session_id": session_id, "message": message,})


def build_http_error_message(exc: HTTPException) -> str:
    if isinstance(exc.detail, str):
        return exc.detail
    return str(exc.detail)

def image_bytes_to_base64(image_data: bytes) -> str:
    return base64.b64encode(image_data).decode("ascii")


async def send_session_ready(websocket: WebSocket, session_id: str) -> None:
    await websocket.send_json({"type": "session_ready", "session_id": session_id,})

async def handle_live_frame_message(websocket: WebSocket, session_id: str, 
                                    client_frame_message: LiveFrameMessage) -> None:
    
    try:
        frame_message = LiveFrameMessage.model_validate(client_frame_message)
    except ValidationError as exc:
        await send_socket_error(websocket, session_id, str(exc))
        return

    if frame_message.session_id != session_id:
        await send_socket_error(websocket, session_id, "Payload session_id does not match websocket session.",)
        return

    if frame_message.image:
        try:
            frame_message.image = image_bytes_to_base64(frame_message.image)          # bytes -> base64 string
        except (base64.binascii.Error, ValueError) as exc:
            await send_socket_error(websocket, session_id, f"Invalid image data: {exc}")
            return

    ai_server_frame_message = LiveFrameMessage_go_ai_server(
        type="frame_base64",
        UUID=frame_message.UUID,
        session_id=frame_message.session_id,
        frame_index=frame_message.frame_index,
        total_frame=frame_message.total_frame,
        image=frame_message.image,
        user_weight=frame_message.user_weight,
    )

    update_live_session_frame_progress(session_id)
    analysis = await analyze_frame_with_ai(session_id, ai_server_frame_message)

    update_live_session_ai_metrics(session_id, analysis)
    client_response = build_live_frame_result_message(session_id, frame_message.frame_index, analysis,)
    
    await websocket.send_json(client_response.model_dump(mode="json"))

async def handle_ping_message(websocket: WebSocket, session_id: str, payload: dict[str, object]) -> None:
    await ping_for_ai_server_connection(session_id)
    await websocket.send_json({"type": "pong", "session_id": session_id,})


@router.websocket("/ws/live/{session_id}")
async def live_session_socket(websocket: WebSocket, session_id: str) -> None:
    ensure_active_live_session(session_id)
    await accept_client_connection(session_id, websocket)

    try:
        await initialize_ai_bridge(session_id)
        await send_session_ready(websocket, session_id)         # 이거 지금 클라꺼임        
        while True:
            payload = await websocket.receive_json()
            
            if not isinstance(payload, dict):
                await send_socket_error(websocket, session_id, "Payload must be a JSON object.",)
                continue

            message_type = payload.get("type", "unknown")
            
            if message_type == "frame_binary":
                try:
                    image_bytes = await websocket.receive_bytes() 
                    
                    client_frame_message = LiveFrameMessage(
                        **payload,
                        image = image_bytes,
                    )

                except ValidationError as exc:
                    await send_socket_error(websocket, session_id, f"Invalid frame message: {exc}")
                    continue
                
                await handle_live_frame_message(websocket, session_id, client_frame_message)
                continue

            # 얘가 AI server 연결 확인
            if message_type == "ping":
                await handle_ping_message(websocket, session_id, payload)
                continue

            if message_type == "pong":
                continue


            await send_socket_error(websocket, session_id, "Unsupported message type.",)
    except WebSocketDisconnect:
        pass
    except HTTPException as exc:
        await send_socket_error(websocket, session_id, build_http_error_message(exc),)
    except (OSError, ConnectionClosed, InvalidStatus, ValidationError, json.JSONDecodeError) as exc:
        await send_socket_error(websocket, session_id, f"AI websocket bridge error: {exc}",)
    finally:
        remove_client_connection(session_id)
