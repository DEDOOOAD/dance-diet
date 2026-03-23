import uvicorn

from servers.general_server.config import HOST, PORT


if __name__ == "__main__":
    uvicorn.run("servers.general_server.server:app", host=HOST, port=PORT, reload=False)
