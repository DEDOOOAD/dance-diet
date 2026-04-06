from __future__ import annotations

import os
from dataclasses import dataclass

from servers.general_server.config import HOST as DEFAULT_HTTP_HOST
from servers.general_server.config import PORT as DEFAULT_HTTP_PORT


@dataclass(slots=True)
class GatewaySettings:
    http_host: str = DEFAULT_HTTP_HOST
    http_port: int = DEFAULT_HTTP_PORT
    grpc_host: str = os.getenv("GRPC_LIVE_HOST", "0.0.0.0")
    grpc_port: int = int(os.getenv("GRPC_LIVE_PORT", "50053"))
    grpc_public_host: str = os.getenv("GRPC_LIVE_PUBLIC_HOST", "127.0.0.1")
    max_message_bytes: int = int(
        os.getenv("GRPC_LIVE_MAX_MESSAGE_BYTES", str(10 * 1024 * 1024))
    )
