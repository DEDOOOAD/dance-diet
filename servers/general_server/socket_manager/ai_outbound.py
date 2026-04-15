from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from websockets.asyncio.client import connect as connect_ai_socket
from websockets.exceptions import ConnectionClosed

from servers.general_server.config import AI_DANCE_WS_PATH, AI_FOOD_WS_PATH, AI_HOST, AI_PORT
from servers.shared.schemas import AiLiveAnalysisMessage, FoodAnalysisRequest, FoodIntakeAnalysisResponse, LiveFrameMessage, LiveFrameMessage_go_ai_server


LOGGER = logging.getLogger(__name__)
MAX_WEBSOCKET_MESSAGE_BYTES = 10_000_000


@dataclass(slots=True)
class AiOutboundConnection:
    websocket: Any
    request_lock: asyncio.Lock


ACTIVE_AI_CONNECTIONS: dict[str, AiOutboundConnection] = {}
AI_CONNECTION_LOCK = asyncio.Lock()


def build_ai_dance_ws_url() -> str:
    return f"ws://{AI_HOST}:{AI_PORT}{AI_DANCE_WS_PATH}"


def build_ai_food_ws_url() -> str:
    return f"ws://{AI_HOST}:{AI_PORT}{AI_FOOD_WS_PATH}"


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


async def analyze_food_with_ai(uuid: str, image_bytes: bytes, image_filename: str | None) -> FoodIntakeAnalysisResponse:
    request_payload = FoodAnalysisRequest(uuid=uuid, image_base64=base64.b64encode(image_bytes).decode("ascii")).model_dump(mode="json")

    try:
        async with connect_ai_socket(build_ai_food_ws_url(), max_size=MAX_WEBSOCKET_MESSAGE_BYTES,) as websocket:
            await websocket.send(json.dumps(request_payload, ensure_ascii=False))
            response_payload = await _recv_food_ai_payload(websocket)
    except (ConnectionClosed, OSError, TimeoutError, json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(status_code=502, detail=f"Food AI server error: {exc}",) from exc

    if response_payload.get("type") == "error":
        raise HTTPException(status_code=502, detail=str(response_payload.get("message", "Food AI server error")),)

    if response_payload.get("foods") in (None, []):
        raise HTTPException(status_code=502, detail="Food AI server returned an empty analysis payload.",)

    normalized_payload = dict(response_payload)
    if normalized_payload.get("source") in (None, ""):
        normalized_payload["source"] = "ai-food-server"
    if normalized_payload.get("image_filename") in (None, ""):
        normalized_payload["image_filename"] = image_filename
    if normalized_payload.get("analyzed_at") in (None, ""):
        normalized_payload["analyzed_at"] = datetime.now().astimezone()

    try:
        return FoodIntakeAnalysisResponse.model_validate(normalized_payload)
    except ValidationError as exc:
        raise HTTPException(status_code=502, detail=f"Invalid Food AI payload: {exc}",) from exc


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

        websocket = await connect_ai_socket(build_ai_dance_ws_url(), max_size=MAX_WEBSOCKET_MESSAGE_BYTES,)
        connection = AiOutboundConnection(websocket=websocket, request_lock=asyncio.Lock(),)
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


async def _recv_food_ai_payload(websocket: Any) -> dict[str, object]:
    for _ in range(3):
        response_raw = await asyncio.wait_for(websocket.recv(), timeout=30.0)
        response_payload = json.loads(response_raw)

        if not isinstance(response_payload, dict):
            raise HTTPException(status_code=502, detail="Food AI payload must be a JSON object.",)

        if response_payload.get("type") in {"ai_ready", "food_ai_ready", "ready"}:
            continue

        return response_payload

    raise HTTPException(status_code=502, detail="Food AI server did not return an analysis payload.",)


async def consume_ai_ready_message(session_id: str, websocket: Any) -> None:
    try:
        ai_ready_raw = await websocket.recv()
    except (ConnectionClosed, OSError):
        await websocket.close()
        raise

    try:
        ai_ready_payload = json.loads(ai_ready_raw)
    except json.JSONDecodeError:
        ai_ready_payload = {"type": "ai_ready"}

    LOGGER.debug("Received AI ready message session_id=%s payload=%s", session_id, ai_ready_payload,)
