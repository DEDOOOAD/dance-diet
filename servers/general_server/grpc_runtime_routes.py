from __future__ import annotations

import logging

from fastapi import APIRouter

from servers.general_server.grpc_live_session_runtime import start_runtime, stop_runtime
from servers.shared.data_schemas import GatewaySettings


LOGGER = logging.getLogger("uvicorn.error.grpc_live_session_runtime")
router = APIRouter()


@router.on_event("startup")
async def startup_grpc_live_session_runtime() -> None:
    await start_runtime(GatewaySettings())
    LOGGER.info("Embedded gRPC live-session runtime is ready")


@router.on_event("shutdown")
async def shutdown_grpc_live_session_runtime() -> None:
    await stop_runtime()
