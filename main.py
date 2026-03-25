import uvicorn

from servers.general_server.config import HOST, PORT, DB_HOST, DB_PORT


if __name__ == "__main__":
    uvicorn.run("servers.general_server.server:app", host=HOST, port=PORT, reload=True)
    # https로 돌릴랬더니 아래의 두 인자가 인증서를 사용해야만 들어갈 수 있는 구조라 다시 HTTP로 변경해서 사용 중 
    # ssl_certfile="cert.pem", ssl_keyfile="key.pem",)
    # 테스트용 DB 서버 실행
    # uvicorn.run("servers.shared.test_db:app", host=DB_HOST, port=DB_PORT, reload=T)
