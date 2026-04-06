from __future__ import annotations

import asyncio


ACTIVE_GRPC_STREAMS: dict[str, asyncio.Queue] = {}


async def connect(session_id: str, response_queue: asyncio.Queue) -> None:
    ACTIVE_GRPC_STREAMS[session_id] = response_queue


def disconnect(session_id: str) -> None:
    ACTIVE_GRPC_STREAMS.pop(session_id, None)


def get_connection(session_id: str) -> asyncio.Queue | None:
    return ACTIVE_GRPC_STREAMS.get(session_id)
