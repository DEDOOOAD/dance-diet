from __future__ import annotations

from fastapi import WebSocket

ACTIVE_CONNECTIONS: dict[str, WebSocket] = {}

async def connect(session_id: str, websocket: WebSocket) -> None:
    await websocket.accept()
    ACTIVE_CONNECTIONS[session_id] = websocket


def disconnect(session_id: str) -> None:
    ACTIVE_CONNECTIONS.pop(session_id, None)


def get_connection(session_id: str) -> WebSocket | None:
    return ACTIVE_CONNECTIONS.get(session_id)
