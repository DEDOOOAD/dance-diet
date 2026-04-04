from __future__ import annotations

import argparse
import importlib
import logging
import os
import sys
import tempfile
from concurrent import futures
from datetime import datetime, timezone
from pathlib import Path

import grpc
from grpc_tools import protoc


LOGGER = logging.getLogger("grpc_preview_server")
SERVICE_VERSION = "0.1.0"
DEFAULT_HOST = os.getenv("GRPC_PREVIEW_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.getenv("GRPC_PREVIEW_PORT", "50051"))
DEFAULT_WORKERS = int(os.getenv("GRPC_PREVIEW_WORKERS", "10"))
PROTO_FILE_PATH = Path(__file__).with_name("dance_diet_preview.proto")


def _read_proto_definition(proto_path: Path) -> str:
    return proto_path.read_text(encoding="utf-8")


def _compile_proto(temp_dir: Path, proto_path: Path):
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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DanceDietPreviewService:
    def __init__(self, pb2) -> None:
        self._pb2 = pb2

    def Ping(self, request, context):
        client_name = request.client_name or "unknown-client"
        message = request.message or "hello"
        LOGGER.info("Ping received from %s: %s", client_name, message)

        return self._pb2.PingResponse(
            ok=True,
            reply=f"pong from grpc server: {message}",
            server_time=_utc_now_iso(),
            service_version=SERVICE_VERSION,
        )

    def SubmitPoseFrame(self, request, context):
        if not request.session_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("session_id is required")
            return self._pb2.PoseFrameResponse()

        landmark_count = len(request.landmarks)
        LOGGER.info(
            "Pose frame received: session_id=%s frame_index=%s landmarks=%s timestamp_ms=%s",
            request.session_id,
            request.frame_index,
            landmark_count,
            request.timestamp_ms,
        )

        return self._pb2.PoseFrameResponse(
            ok=True,
            received_landmark_count=landmark_count,
            note=(
                f"Accepted frame {request.frame_index} "
                f"for session {request.session_id}"
            ),
            received_at=_utc_now_iso(),
        )


def serve(host: str, port: int, workers: int) -> None:
    if not PROTO_FILE_PATH.exists():
        raise FileNotFoundError(f"Proto file not found: {PROTO_FILE_PATH}")

    with tempfile.TemporaryDirectory(prefix="grpc_preview_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        pb2, pb2_grpc = _compile_proto(temp_dir, PROTO_FILE_PATH)

        server = grpc.server(futures.ThreadPoolExecutor(max_workers=workers))
        pb2_grpc.add_DanceDietPreviewServiceServicer_to_server(
            DanceDietPreviewService(pb2),
            server,
        )

        bind_target = f"{host}:{port}"
        bound_port = server.add_insecure_port(bind_target)
        if bound_port == 0:
            raise RuntimeError(f"Failed to bind gRPC server to {bind_target}")
        server.start()

        LOGGER.info("gRPC preview server started on %s", bind_target)
        LOGGER.info("Share the proto with the client using: python -m servers.general_server.grpc_preview_server --print-proto")

        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            LOGGER.info("Stopping gRPC preview server")
            server.stop(2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Single-file gRPC preview server for client integration tests."
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Bind port")
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Thread pool worker count",
    )
    parser.add_argument(
        "--print-proto",
        action="store_true",
        help="Print the proto definition used by this server and exit",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = parse_args()

    if args.print_proto:
        print(_read_proto_definition(PROTO_FILE_PATH).strip())
        return

    serve(host=args.host, port=args.port, workers=args.workers)


if __name__ == "__main__":
    main()
