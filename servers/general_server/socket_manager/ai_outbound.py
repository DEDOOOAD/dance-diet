from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass

from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from websockets.asyncio.client import connect as connect_ai_socket
from websockets.exceptions import ConnectionClosed

from servers.general_server.config import AI_HOST, AI_PORT, AI_DANCE_WS_PATH
from servers.shared.schemas import AiLiveAnalysisMessage, LiveFrameMessage_go_ai_server


LOGGER = logging.getLogger(__name__)
MAX_WEBSOCKET_MESSAGE_BYTES = 10_000_000


@dataclass(slots=True)
class AiOutboundConnection:
    websocket: Any
    request_lock: asyncio.Lock


ACTIVE_AI_CONNECTIONS: dict[str, AiOutboundConnection] = {}
AI_CONNECTION_LOCK = asyncio.Lock()


def build_ai_dance_ws_url(session_id: str) -> str:
    dance_ws_path = AI_DANCE_WS_PATH.strip("/")
    return f"ws://{AI_HOST}:{AI_PORT}/{dance_ws_path}/{session_id}"


# initai connection
async def initialize_ai_bridge(session_id: str) -> None:
    await get_or_create_ai_connection(session_id)


async def analyze_frame_with_ai(session_id: str, frame_message: LiveFrameMessage_go_ai_server) -> AiLiveAnalysisMessage:
    ai_response_payload = await exchange_ai_message(session_id, frame_message.model_dump(mode="json"),)

    if ai_response_payload.get("type") == "error":
        raise HTTPException(status_code=502, detail=str(ai_response_payload.get("message", "AI server error")),)

    try:
        return AiLiveAnalysisMessage.model_validate(ai_response_payload)
    except ValidationError as exc:
        raise HTTPException(status_code=502, detail=f"Invalid AI analysis payload: {exc}",) from exc


async def ping_for_ai_server_connection(session_id: str) -> None:
    await exchange_ai_message(session_id, {"type": "ping", "session_id": session_id,},)


async def close_ai_connection(session_id: str) -> None:
    async with AI_CONNECTION_LOCK:
        connection = ACTIVE_AI_CONNECTIONS.pop(session_id, None)

    if connection is None:
        return

    try:
        await connection.websocket.close()
    except Exception:
        LOGGER.debug("AI websocket close failed session_id=%s", session_id, exc_info=True,)


async def get_or_create_ai_connection(session_id: str) -> AiOutboundConnection:
    existing_connection = ACTIVE_AI_CONNECTIONS.get(session_id)
    if existing_connection is not None:
        return existing_connection

    async with AI_CONNECTION_LOCK:
        existing_connection = ACTIVE_AI_CONNECTIONS.get(session_id)
        if existing_connection is not None:
            return existing_connection

        websocket = await connect_ai_socket(build_ai_dance_ws_url(session_id), max_size=MAX_WEBSOCKET_MESSAGE_BYTES,)
        connection = AiOutboundConnection(websocket=websocket, request_lock=asyncio.Lock(),)

        LOGGER.debug("=============================================")
        LOGGER.debug("connection data: ", connection)
        LOGGER.debug("=============================================")

        await consume_ai_ready_message(session_id, websocket)

        ACTIVE_AI_CONNECTIONS[session_id] = connection

        return connection


async def exchange_ai_message(session_id: str, payload: dict[str, object]) -> dict[str, object]:
    try:
        return await _exchange_ai_message(session_id, payload)
    except (ConnectionClosed, OSError):
        await close_ai_connection(session_id)
        return await _exchange_ai_message(session_id, payload)


async def _exchange_ai_message(session_id: str, payload: dict[str, object]) -> dict[str, object]:
    connection = await get_or_create_ai_connection(session_id)

    async with connection.request_lock:
        await connection.websocket.send(json.dumps(payload, ensure_ascii=False))
        response_raw = await connection.websocket.recv()

    return json.loads(response_raw)


async def consume_ai_ready_message(session_id: str, websocket: Any) -> None:
    try:
        ai_ready_raw = await websocket.recv()
        LOGGER.debug("Received AI ready message session_id=%s payload=%s", session_id, ai_ready_raw)
    except (ConnectionClosed, OSError):
        await websocket.close()
        LOGGER.debug("Failed")
        raise
