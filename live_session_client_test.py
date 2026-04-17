from __future__ import annotations

import argparse
import asyncio
import base64
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import cv2
from websockets.asyncio.client import connect


DEFAULT_SERVER = "http://127.0.0.1:8000"        # 이거는 클라이언트가 알아서 맞춰야함
DEFAULT_SOURCE = "test.gif"
DEFAULT_TARGET_FPS = 16.0
DEFAULT_DURATION_SECONDS = 600
PREVIEW_WINDOW = "Live Session Client Preview"


# 설명
# post_json()
# session start/end 같은 HTTP request(요청)를 보내고
# JSON response(응답)를 받아 테스트 client(클라이언트)에서 바로 쓰게 해준다.
def post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST",)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} calling {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc}") from exc


# 설명
# encode_frame_to_base64()
# OpenCV frame(프레임)을 JPEG bytes(바이트)로 인코딩한 뒤,
# websocket(WebSocket) payload에 실을 수 있도록 base64 string(문자열)로 바꾼다.
def encode_frame_to_base64(frame) -> str:
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        raise RuntimeError("Failed to encode frame to JPEG")
    return base64.b64encode(buffer.tobytes()).decode("ascii")


# 설명
# iter_source_frames()
# source video(소스 영상)나 GIF에서 frame(프레임)을 하나씩 읽어서
# frame index(순번), timestamp(시각), 실제 frame data(데이터)를 순서대로 내보낸다.
def iter_source_frames(source_path: Path, max_frames: int | None):
    cap = cv2.VideoCapture(str(source_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open source file: {source_path}")

    frame_index = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
            yield frame_index, timestamp_ms, frame
            frame_index += 1

            if max_frames is not None and frame_index >= max_frames:
                break
    finally:
        cap.release()


# 설명
# draw_overlay()
# 현재 전송 중인 session 상태와 ack(response) 정보를 frame 위에 그려서
# 실시간 websocket(WebSocket) 테스트 상황을 화면에서 확인하게 해준다.
def draw_overlay(
    frame,
    *,
    session_id: str,
    frame_index: int,
    timestamp_ms: int,
    ack_payload: dict[str, object] | None,
    round_trip_ms: float | None,
    sent_frames: int,
):
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (frame.shape[1], 120), (20, 20, 20), -1)
    blended = cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)

    lines = [
        f"session: {session_id[:18]}...",
        f"frame_index: {frame_index}  timestamp_ms: {timestamp_ms}",
        f"sent_frames: {sent_frames}",
    ]

    if ack_payload is not None:
        lines.append("ack: accepted={accepted} total_frames={total_frames}".format(accepted=ack_payload.get("accepted"), total_frames=ack_payload.get("total_frames"),))
    if round_trip_ms is not None:
        lines.append(f"round_trip_ms: {round_trip_ms:.1f}")

    y = 28
    for line in lines:
        cv2.putText(blended, line, (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA,)
        y += 24

    return blended


# 설명
# show_preview()
# OpenCV preview window(미리보기 창)에 현재 frame(프레임)을 출력하고,
# 사용자가 종료 키를 눌렀는지 확인한다.
def show_preview(frame) -> bool:
    cv2.imshow(PREVIEW_WINDOW, frame)
    key = cv2.waitKey(1) & 0xFF
    return key != ord("q")


# 설명
# run_client()
# HTTP session start(세션 시작) 요청, websocket(WebSocket) 연결,
# frame streaming(프레임 스트리밍), session end(세션 종료) 요청까지 전체 테스트 흐름을 실행한다.
async def run_client(
    server_base_url: str,
    source_path: Path,
    uuid: str,
    dance_type: str,
    content_id: str,
    target_fps: float,
    max_frames: int | None,
    preview: bool,
) -> None:
    print(f"[1/4] Starting live session on {server_base_url}")
    start_response = post_json(f"{server_base_url}/api/live/session/start", {"uuid": uuid, "dance_type": dance_type, "content_id": content_id,},)
    session_id = str(start_response["session_id"])
    ws_url = str(start_response["ws_url"])
    print(f"  session_id={session_id}")
    print(f"  ws_url={ws_url}")

    frame_interval = 1.0 / target_fps
    sent_frames = 0

    print("[2/4] Connecting WebSocket")
    async with connect(ws_url, max_size=10_000_000) as websocket:
        initial_message = await websocket.recv()
        print(f"  server={initial_message}")

        print(f"[3/4] Sending frames from {source_path} at {target_fps:.2f} fps")
        next_send_time = time.perf_counter()

        if preview:
            cv2.namedWindow(PREVIEW_WINDOW, cv2.WINDOW_NORMAL)

        try:
            for frame_index, timestamp_ms, frame in iter_source_frames(source_path, max_frames):
                now = time.perf_counter()
                if now < next_send_time:
                    await asyncio.sleep(next_send_time - now)

                payload = {
                    "type": "frame",
                    "UUID": uuid,
                    "session_id": session_id,
                    "frame_index": frame_index,
                    "total_frame": sent_frames + 1,
                    "timestamp_ms": timestamp_ms if timestamp_ms > 0 else int(frame_index * frame_interval * 1000),
                    "image_base64": encode_frame_to_base64(frame),
                }

                send_started = time.perf_counter()
                await websocket.send(json.dumps(payload))
                ack_raw = await websocket.recv()
                round_trip_ms = (time.perf_counter() - send_started) * 1000
                ack_payload = json.loads(ack_raw)

                sent_frames += 1
                print(f"  frame={frame_index} ack={ack_raw}")

                if preview:
                    preview_frame = draw_overlay(frame, session_id=session_id, frame_index=frame_index, timestamp_ms=int(payload["timestamp_ms"]), ack_payload=ack_payload, round_trip_ms=round_trip_ms, sent_frames=sent_frames,)
                    if not show_preview(preview_frame):
                        print("  preview closed by user; stopping early")
                        break

                next_send_time += frame_interval
        finally:
            if preview:
                cv2.destroyWindow(PREVIEW_WINDOW)

        print(f"  sent_frames={sent_frames}")

    print("[4/4] Ending live session")
    end_response = post_json(f"{server_base_url}/api/live/session/end", {"session_id": session_id,},)
    print(f"  end_response={json.dumps(end_response, ensure_ascii=False)}")


# 설명
# parse_args()
# 테스트 client(클라이언트) 실행에 필요한 server 주소, source 파일,
# fps(초당 프레임 수), preview 옵션을 command line argument(명령행 인자)로 받는다.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="One-off local client for testing the live dance session HTTP + WebSocket flow.",)
    parser.add_argument("--server", default=DEFAULT_SERVER, help="General server base URL")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="Local GIF/video file to stream as frames")
    parser.add_argument("--uuid", default="local-test-user", help="UUID used when creating the live session")
    parser.add_argument("--dance-type", default="kpop", help="Dance type sent to the session start API")
    parser.add_argument("--content-id", default="mission-1", help="Content ID sent to the session start API")
    parser.add_argument("--fps", type=float, default=DEFAULT_TARGET_FPS, help="Target send rate in frames per second")
    parser.add_argument("--duration-seconds", type=int, default=DEFAULT_DURATION_SECONDS, help="Streaming duration in seconds. Default is 600 seconds (10 minutes).",)
    parser.add_argument("--max-frames", type=int, default=None, help="Maximum number of frames to send. If omitted, duration_seconds * fps is used.",)
    parser.add_argument("--no-preview", action="store_true", help="Disable the OpenCV preview window",)
    return parser.parse_args()


# 설명
# main()
# command line argument(명령행 인자)를 읽고 입력값을 정리한 뒤,
# websocket(WebSocket) 테스트 client(클라이언트)를 실제로 실행한다.
def main() -> None:
    args = parse_args()
    source_path = Path(args.source)
    if not source_path.exists():
        raise SystemExit(f"Source file not found: {source_path}")

    max_frames = args.max_frames
    if max_frames is None:
        max_frames = int(args.duration_seconds * args.fps)

    asyncio.run(run_client(server_base_url=args.server.rstrip("/"), source_path=source_path, uuid=args.uuid, dance_type=args.dance_type, content_id=args.content_id, target_fps=args.fps, max_frames=max_frames, preview=not args.no_preview,))


if __name__ == "__main__":
    main()
