from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path

import grpc
from fastapi import HTTPException
from grpc_tools import protoc

from servers.general_server.grpc_session_manager import (
    calculate_dance_elapsed_seconds,
    create_live_session,
    end_live_session,
    record_live_session_frame,
    require_active_session,
)
from servers.general_server.grpc_stream_manager import connect, disconnect
from servers.shared.schemas import LiveSessionStartRequest


STREAM_METHOD = "/dance_diet.live.v1.DanceDietLiveSessionService/StreamLiveSession"
PROTO_SERVICE = "dance_diet.live.v1.DanceDietLiveSessionService"
PROTO_FILE_PATH = Path(__file__).with_name("dance_diet_live_session.proto")


def utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def read_proto_definition(proto_path: Path) -> str:
    return proto_path.read_text(encoding="utf-8")


def compile_proto(temp_dir: Path, proto_path: Path):
    module_name = f"{proto_path.stem}_pb2"
    grpc_module_name = f"{proto_path.stem}_pb2_grpc"

    result = protoc.main(
        [
            "grpc_tools.protoc",
            f"-I{proto_path.parent}",
            f"--python_out={temp_dir}",
            f"--grpc_python_out={temp_dir}",
            str(proto_path),
        ]
    )
    if result != 0:
        raise RuntimeError(f"Failed to compile proto definition (exit code: {result})")

    sys.path.insert(0, str(temp_dir))
    pb2 = importlib.import_module(module_name)
    pb2_grpc = importlib.import_module(grpc_module_name)
    return pb2, pb2_grpc


class DanceDietLiveSessionService:
    def __init__(self, pb2, grpc_target: str) -> None:
        self._pb2 = pb2
        self._grpc_target = grpc_target

    async def StartLiveSession(self, request, context: grpc.aio.ServicerContext):
        if not request.user_id:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "user_id is required")

        session = create_live_session(
            LiveSessionStartRequest(
                user_id=request.user_id,
                dance_type=request.dance_type or None,
                content_id=request.content_id or None,
            ),
            self._grpc_target,
            STREAM_METHOD,
        )
        return self._pb2.LiveSessionStartResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            status=session.status,
            started_at=session.started_at.isoformat(),
            grpc_target=self._grpc_target,
            stream_method=STREAM_METHOD,
            dance_type=session.dance_type or "",
            content_id=session.content_id or "",
        )

    async def EndLiveSession(self, request, context: grpc.aio.ServicerContext):
        if not request.session_id:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "session_id is required")

        try:
            session = end_live_session(request.session_id)
        except HTTPException as exc:
            await self._abort_for_http_exception(context, exc)

        return self._pb2.LiveSessionEndResponse(
            session_id=session.session_id,
            status=session.status,
            ended_at=session.ended_at.isoformat() if session.ended_at else "",
            total_frames=session.total_frames,
            elapsed_seconds=session.elapsed_seconds,
            total_calories=session.total_calories,
            message="Session ended successfully.",
        )

    async def StreamLiveSession(self, request_iterator, context: grpc.aio.ServicerContext):
        response_queue: asyncio.Queue = asyncio.Queue()
        stream_state = {
            "session_id": "",
            "connected": False,
            "closed": False,
        }

        async def consume_requests() -> None:
            try:
                async for event in request_iterator:
                    response = await self._handle_client_event(
                        event,
                        stream_state,
                        context,
                        response_queue,
                    )
                    if response is not None:
                        await response_queue.put(response)

                    if stream_state["closed"]:
                        break
            except grpc.RpcError:
                raise
            except Exception as exc:  # pragma: no cover
                await response_queue.put(
                    self._build_server_event(
                        event_type=self._pb2.SERVER_EVENT_WARNING,
                        event_name="error",
                        session_id=str(stream_state["session_id"]),
                        message=str(exc),
                    )
                )
            finally:
                session_id = str(stream_state["session_id"])
                if session_id:
                    disconnect(session_id)
                await response_queue.put(None)

        consumer_task = asyncio.create_task(consume_requests())

        try:
            while True:
                response = await response_queue.get()
                if response is None:
                    break
                yield response
        finally:
            if not consumer_task.done():
                consumer_task.cancel()
            await asyncio.gather(consumer_task, return_exceptions=True)

    async def _handle_client_event(
        self,
        event,
        stream_state,
        context: grpc.aio.ServicerContext,
        response_queue: asyncio.Queue,
    ):
        event_type = event.event_type

        if event_type == self._pb2.CLIENT_EVENT_SESSION_JOIN:
            join_payload = event.join
            if not join_payload.session_id:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "session_id is required")

            try:
                require_active_session(join_payload.session_id)
            except HTTPException as exc:
                await self._abort_for_http_exception(context, exc)

            stream_state["session_id"] = join_payload.session_id
            stream_state["connected"] = True
            await connect(join_payload.session_id, response_queue)

            return self._build_server_event(
                event_type=self._pb2.SERVER_EVENT_SESSION_READY,
                event_name="session_ready",
                session_id=join_payload.session_id,
                message="Stream connected",
            )

        if event_type == self._pb2.CLIENT_EVENT_FRAME:
            frame = event.frame
            if not stream_state["connected"]:
                return self._build_server_event(
                    event_type=self._pb2.SERVER_EVENT_WARNING,
                    event_name="error",
                    session_id="",
                    message="Join the session before sending frames.",
                )

            session_id = str(stream_state["session_id"])
            try:
                session = record_live_session_frame(session_id)
            except HTTPException as exc:
                await self._abort_for_http_exception(context, exc)

            return self._build_server_event(
                event_type=self._pb2.SERVER_EVENT_FRAME_ACK,
                event_name="frame_ack",
                session_id=session_id,
                frame_index=frame.frame_index,
                total_frames=int(session["total_frames"]),
                elapsed_seconds=calculate_dance_elapsed_seconds(session),
                total_calories=float(session["total_calories"]),
                source_timestamp_ms=frame.timestamp_ms,
                image_format=frame.image_format,
                frame_byte_size=len(frame.frame_bytes),
            )

        if event_type == self._pb2.CLIENT_EVENT_PING:
            if not stream_state["connected"]:
                return self._build_server_event(
                    event_type=self._pb2.SERVER_EVENT_WARNING,
                    event_name="error",
                    session_id="",
                    message="Join the session before sending ping.",
                )

            return self._build_server_event(
                event_type=self._pb2.SERVER_EVENT_PONG,
                event_name="pong",
                session_id=str(stream_state["session_id"]),
            )

        if event_type == self._pb2.CLIENT_EVENT_STREAM_CLOSE:
            session_id = str(stream_state["session_id"])
            if session_id:
                disconnect(session_id)
            stream_state["closed"] = True
            stream_state["connected"] = False
            return None

        return self._build_server_event(
            event_type=self._pb2.SERVER_EVENT_WARNING,
            event_name="error",
            session_id=str(stream_state["session_id"]),
            message="Unsupported message type",
        )

    async def _abort_for_http_exception(
        self,
        context: grpc.aio.ServicerContext,
        exc: HTTPException,
    ) -> None:
        detail = str(exc.detail)
        if exc.status_code == 404:
            await context.abort(grpc.StatusCode.NOT_FOUND, detail)
        if exc.status_code == 400:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, detail)
        await context.abort(grpc.StatusCode.INTERNAL, detail)

    def _build_server_event(
        self,
        *,
        event_type: int,
        event_name: str,
        session_id: str,
        frame_index: int = 0,
        total_frames: int = 0,
        elapsed_seconds: float = 0.0,
        total_calories: float = 0.0,
        status: str = "",
        message: str = "",
        dance_type: str = "",
        content_id: str = "",
        source_timestamp_ms: int = 0,
        image_format: int = 0,
        frame_byte_size: int = 0,
    ):
        return self._pb2.LiveSessionServerEvent(
            event_type=event_type,
            type=event_name,
            session_id=session_id,
            frame_index=frame_index,
            total_frames=total_frames,
            elapsed_seconds=elapsed_seconds,
            total_calories=total_calories,
            status=status,
            message=message,
            emitted_at=utc_now_iso(),
            grpc_target=self._grpc_target,
            stream_method=STREAM_METHOD,
            dance_type=dance_type,
            content_id=content_id,
            source_timestamp_ms=source_timestamp_ms,
            image_format=image_format,
            frame_byte_size=frame_byte_size,
        )
