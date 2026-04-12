from __future__ import annotations

from fastapi import WebSocket
from starlette.websockets import WebSocketState


ACTIVE_CLIENT_CONNECTIONS: dict[str, WebSocket] = {}


async def accept_client_connection(session_id: str, websocket: WebSocket) -> None:
    await websocket.accept()
    ACTIVE_CLIENT_CONNECTIONS[session_id] = websocket


def remove_client_connection(session_id: str) -> None:
    ACTIVE_CLIENT_CONNECTIONS.pop(session_id, None)


def get_client_connection(session_id: str) -> WebSocket | None:
    return ACTIVE_CLIENT_CONNECTIONS.get(session_id)


async def close_client_connection(session_id: str, *, code: int = 1000, reason: str | None = None) -> None:
    websocket = ACTIVE_CLIENT_CONNECTIONS.pop(session_id, None)
    if websocket is None:
        return

    if websocket.application_state == WebSocketState.DISCONNECTED:
        return

    try:
        await websocket.close(code=code, reason=reason)
    except RuntimeError:
        return
