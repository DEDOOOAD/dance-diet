from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import grpc

from servers.general_server.grpc_stream_routes import (
    PROTO_FILE_PATH,
    DanceDietLiveSessionService,
    compile_proto,
)
from servers.shared.data_schemas import GatewaySettings


LOGGER = logging.getLogger("uvicorn.error.grpc_live_session_runtime")
_RUNTIME: GrpcLiveSessionRuntime | None = None


def build_grpc_target(host: str, port: int, public_host: str) -> str:
    resolved_host = public_host if host == "0.0.0.0" else host
    return f"{resolved_host}:{port}"


class GrpcLiveSessionRuntime:
    def __init__(self, settings: GatewaySettings) -> None:
        self._settings = settings
        self._server: grpc.aio.Server | None = None
        self._temp_dir: tempfile.TemporaryDirectory[str] | None = None
        self._grpc_target = build_grpc_target(
            settings.grpc_host,
            settings.grpc_port,
            settings.grpc_public_host,
        )

    @property
    def grpc_target(self) -> str:
        return self._grpc_target

    async def start(self) -> None:
        if self._server is not None:
            return

        if not PROTO_FILE_PATH.exists():
            raise FileNotFoundError(f"Proto file not found: {PROTO_FILE_PATH}")

        self._temp_dir = tempfile.TemporaryDirectory(prefix="grpc_live_session_runtime_")
        temp_dir = Path(self._temp_dir.name)
        pb2, pb2_grpc = compile_proto(temp_dir, PROTO_FILE_PATH)

        server = grpc.aio.server(
            options=[
                ("grpc.max_send_message_length", self._settings.max_message_bytes),
                ("grpc.max_receive_message_length", self._settings.max_message_bytes),
            ]
        )
        pb2_grpc.add_DanceDietLiveSessionServiceServicer_to_server(
            DanceDietLiveSessionService(pb2, self._grpc_target),
            server,
        )

        bind_target = f"{self._settings.grpc_host}:{self._settings.grpc_port}"
        bound_port = server.add_insecure_port(bind_target)
        if bound_port == 0:
            raise RuntimeError(f"Failed to bind gRPC server to {bind_target}")

        await server.start()
        self._server = server
        LOGGER.info("Started embedded gRPC live-session runtime on %s", bind_target)

    async def stop(self) -> None:
        if self._server is not None:
            await self._server.stop(2)
            self._server = None

        if self._temp_dir is not None:
            self._temp_dir.cleanup()
            self._temp_dir = None


async def start_runtime(settings: GatewaySettings | None = None) -> GrpcLiveSessionRuntime:
    global _RUNTIME

    if _RUNTIME is None:
        _RUNTIME = GrpcLiveSessionRuntime(settings or GatewaySettings())

    await _RUNTIME.start()
    return _RUNTIME


async def stop_runtime() -> None:
    global _RUNTIME

    if _RUNTIME is None:
        return

    await _RUNTIME.stop()
    _RUNTIME = None


def get_runtime() -> GrpcLiveSessionRuntime:
    if _RUNTIME is None:
        raise RuntimeError("gRPC live-session runtime is not started")
    return _RUNTIME
