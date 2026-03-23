import uvicorn

from servers.ai_server.config import HOST, PORT


if __name__ == "__main__":
    uvicorn.run("servers.ai_server.server:app", host=HOST, port=PORT, reload=False)
