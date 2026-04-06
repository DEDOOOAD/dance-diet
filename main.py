import logging

import uvicorn

from servers.general_server.config import HOST, PORT


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    uvicorn.run(
        "servers.general_server.server:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info",
    )
