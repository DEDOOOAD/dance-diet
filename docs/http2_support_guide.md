# HTTP/2 지원 방법 정리

이 문서는 현재 저장소 상태에서 일반 API 서버에 HTTP/2를 붙이는 현실적인 방법을 정리한다.

기준 시점의 현재 구조:

- `main.py`에서 `uvicorn.run("servers.general_server.server:app", ...)`으로 서버를 실행한다.
- 실제 앱은 `servers/general_server/server.py`의 FastAPI ASGI 앱이다.
- 현재 의존성에는 `uvicorn`이 있고 `hypercorn`은 직접 추가되어 있지 않다.
- 일반 API 외에 별도 gRPC 사용 흔적이 있으므로, REST/WebSocket과 gRPC는 분리해서 생각하는 편이 안전하다.

## 핵심 결론

현재 코드베이스에서 HTTP/2를 지원하는 방법은 크게 2가지다.

1. 가장 현실적인 방법: `Uvicorn`은 그대로 두고, 앞단에 HTTP/2 가능한 리버스 프록시를 둔다.
2. 서버 자체가 직접 HTTP/2를 말해야 한다면: `Uvicorn` 대신 `Hypercorn`으로 실행한다.

이 프로젝트 기준 추천 순서는 다음과 같다.

- 외부 클라이언트가 HTTP/2로 붙기만 하면 된다: 리버스 프록시 방식 추천
- FastAPI 서버 프로세스 자체가 직접 HTTP/2를 받아야 한다: Hypercorn 방식 추천

## 왜 지금 상태에서 바로 안 되는가

현재 엔트리포인트는 `Uvicorn`을 사용한다. Uvicorn 공식 문서는 현재 지원 범위를 HTTP/1.1과 WebSocket으로 설명하고 있다. 즉, `ssl_certfile`과 `ssl_keyfile`만 붙여도 HTTPS는 될 수 있지만, 그것만으로 HTTP/2가 켜지지는 않는다.

정리하면:

- `Uvicorn + TLS`는 HTTPS일 수는 있어도, HTTP/2 보장은 아니다.
- HTTP/2를 원하면 서빙 계층을 바꿔야 한다.

## 방법 1. 앞단 프록시로 HTTP/2 제공하기

이 방법이 현재 저장소에는 가장 부담이 적다.

구성은 다음과 같다.

```text
Client (HTTP/2)
  -> Caddy / Nginx / Traefik
  -> Uvicorn + FastAPI (HTTP/1.1)
```

장점:

- 앱 코드 수정이 거의 없다.
- 현재 `main.py`와 `servers/general_server/server.py`를 그대로 유지할 수 있다.
- TLS 인증서 관리, HTTPS 리다이렉트, 공개 도메인 처리를 프록시가 맡아준다.
- 점진 도입이 쉽다.

주의:

- 클라이언트와 프록시 사이만 HTTP/2다.
- 프록시와 Uvicorn 사이는 일반적으로 HTTP/1.1이다.
- 그래도 외부 사용자가 체감하는 "HTTP/2 지원" 목적에는 보통 충분하다.

### 추천 프록시: Caddy

현재 문서 기준으로는 Caddy가 가장 간단하다.

- 자동 HTTPS 지원
- 기본적으로 현대 HTTP 버전을 활성화
- `reverse_proxy` 설정이 단순함

예시 Caddyfile:

```caddyfile
api.example.com {
    encode zstd gzip
    reverse_proxy 127.0.0.1:8000
}
```

적용 순서:

1. FastAPI 서버를 내부 포트에서 실행한다.

```powershell
uv run python main.py
```

2. Caddy가 같은 머신에서 `127.0.0.1:8000`으로 프록시하게 둔다.

3. 외부 클라이언트는 `https://api.example.com/...`으로 접근한다.

4. 검증은 다음처럼 한다.

```powershell
curl.exe -I --http2 https://api.example.com/api/app
```

응답 첫 줄이 `HTTP/2 200`처럼 보이면 프론트 도달 구간은 HTTP/2로 동작한 것이다.

### 이 방식이 현재 프로젝트에 잘 맞는 이유

- 현재 실행 로직이 이미 `main.py -> Uvicorn -> FastAPI`로 단순하다.
- `servers/general_server/server.py` 안에는 일반 REST 라우트와 WebSocket 라우트가 함께 있다.
- 서빙 레이어만 프록시로 감싸면, 애플리케이션 로직을 거의 건드리지 않고 공개 HTTP/2를 붙일 수 있다.

## 방법 2. Uvicorn 대신 Hypercorn으로 직접 HTTP/2 받기

서버 프로세스 자체가 직접 HTTP/2 연결을 처리해야 한다면 `Hypercorn`으로 교체하는 편이 맞다.

구성은 다음과 같다.

```text
Client (HTTP/2)
  -> Hypercorn + FastAPI
```

장점:

- ASGI 서버가 직접 HTTP/2를 처리한다.
- 프록시 없이도 HTTP/2 테스트가 가능하다.

주의:

- 현재 저장소에는 `hypercorn` 의존성이 없다.
- 실행 스크립트나 배포 명령을 바꿔야 한다.
- 브라우저나 모바일 클라이언트에서 실제 HTTP/2를 쓰려면 보통 TLS가 필요하다.

### 필요한 변경

1. 의존성 추가

```powershell
uv add hypercorn
```

2. 실행 명령 변경

```powershell
uv run hypercorn --bind 0.0.0.0:8443 --certfile cert.pem --keyfile key.pem servers.general_server.server:app
```

3. 검증

```powershell
curl.exe -I --http2 https://127.0.0.1:8443/api/app --insecure
```

브라우저 기반 실제 테스트를 할 계획이면, 로컬에서도 신뢰 가능한 인증서 구성이 같이 필요하다.

### h2c에 대한 메모

Hypercorn은 TLS 없이도 `h2c` 업그레이드 방식 테스트를 지원한다. 다만 대부분의 브라우저는 실제 HTTP/2를 TLS 위에서 기대하므로, 내부 테스트용이 아니라면 HTTPS 기준으로 보는 편이 맞다.

## 현재 저장소 기준 권장안

현재 프로젝트에서는 다음 우선순위를 추천한다.

### 1순위: Caddy 같은 프록시를 앞단에 두기

이 경우 적합한 상황:

- 앱 사용자에게 "이 서버는 HTTP/2로 서비스된다"를 빠르게 제공하고 싶다.
- 현재 `main.py`와 서버 코드 변경을 최소화하고 싶다.
- 배포 안정성을 우선한다.

### 2순위: Hypercorn으로 직접 전환하기

이 경우 적합한 상황:

- 프록시 없이도 서버가 직접 HTTP/2를 처리해야 한다.
- 테스트 환경이나 내부 서비스 호출에서도 h2가 중요하다.
- 실행/배포 방식 변경을 감수할 수 있다.

## 이 프로젝트에서 피해야 할 오해

다음은 HTTP/2 지원으로 보지 않는 편이 맞다.

- `main.py`에서 주석 처리된 `ssl_certfile`, `ssl_keyfile`만 켜는 것
- `uv.lock` 안에 `h2` 패키지가 보인다는 이유만으로 서버가 HTTP/2라고 판단하는 것

둘 다 "HTTP/2 가능성"과는 별개로, 실제 서빙 서버가 무엇을 지원하느냐가 결정적이다.

## 추천 실행 전략

가장 안전한 진행 순서는 아래와 같다.

1. 먼저 Caddy 앞단 프록시로 공개 HTTP/2를 붙인다.
2. 실제 모바일 앱이나 클라이언트에서 문제 없이 동작하는지 확인한다.
3. 그 다음에도 서버 자체 h2가 꼭 필요할 때만 Hypercorn 전환을 검토한다.

## 참고 자료

- Uvicorn 문서: 현재 지원 범위를 HTTP/1.1과 WebSocket으로 설명
  - https://www.uvicorn.org/
  - https://www.uvicorn.org/settings/
- Hypercorn 문서: HTTP/1, HTTP/2, WebSocket 지원 및 TLS/ALPN, h2c 설명
  - https://hypercorn.readthedocs.io/en/latest/index.html
  - https://hypercorn.readthedocs.io/en/latest/discussion/http2.html
  - https://hypercorn.readthedocs.io/en/latest/how_to_guides/configuring.html
- FastAPI 문서: 프록시 뒤에서 운용하는 일반적인 패턴 설명
  - https://fastapi.tiangolo.com/advanced/behind-a-proxy/
- Caddy 문서: 자동 HTTPS, HTTP 버전, reverse proxy
  - https://caddyserver.com/docs/automatic-https
  - https://caddyserver.com/features
  - https://caddyserver.com/docs/caddyfile/directives/reverse_proxy
