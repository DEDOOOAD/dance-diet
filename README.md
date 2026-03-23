# Split Server Scaffold

This project is organized as two separate FastAPI servers: a general REST API server and an AI analysis server.

> License note: A project license will be reviewed and added later.

## Structure

- `servers/general_server/`: general REST API server for app-facing endpoints
- `servers/ai_server/`: AI analysis server for pose and GIF processing
- `servers/shared/`: shared Pydantic schemas used by both servers

## Run

Install dependencies first, then start each server in a separate terminal.

```powershell
uv run python main.py
```

```powershell
uv run python ai_server_main.py
```

General server:

- `GET /health`
- `GET /docs`
- `GET /openapi.json`
- `GET /ai`
- `GET /api/app`
- `GET /api/home`
- `GET /api/classes`
- `GET /api/records?period=weekly`
- `GET /api/profile`
- `GET /api/settings`
- `GET /api/achievements`
- `POST /api/live/session/start`
- `POST /api/live/session/end`
- `WS /ws/live/{session_id}`
- `POST /api/settings/toggles`

AI server:

- `GET /health`
- `GET /docs`
- `GET /openapi.json`
- `POST /analyze/pose`
- `POST /analyze/gif`

## Swagger test

After both servers are running, open these FastAPI Swagger pages:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8001/docs`

Or load these OpenAPI specs directly:

- `http://127.0.0.1:8000/openapi.json`
- `http://127.0.0.1:8001/openapi.json`

## Mock-data APIs for app tabs

The general server includes mock APIs mapped from the app tab screens:

- `home` tab: `/api/home`
- `classes` tab: `/api/classes?genre=K-POP&search=Min`
- `record` tab: `/api/records?period=weekly`
- `profile` tab: `/api/profile`

Example toggle update:

```json
POST /api/settings/toggles
{
  "key": "dark_mode",
  "value": false
}
```

Example live session start:

```json
POST /api/live/session/start
{
  "user_id": "user-1",
  "dance_type": "kpop",
  "content_id": "mission-1"
}
```

Example WebSocket flow:

1. Call `POST /api/live/session/start`
2. Read the returned `ws_url`
3. Connect to `WS /ws/live/{session_id}`
4. Send messages like:

```json
{
  "type": "frame",
  "frame_index": 1,
  "timestamp_ms": 33,
  "image_base64": "..."
}
```

## Split architecture

```text
servers/
├─ general_server/
│  ├─ config.py
│  ├─ mock_data.py
│  └─ server.py
├─ ai_server/
│  ├─ config.py
│  ├─ server.py
│  └─ services/
│     ├─ gif_pose_service.py
│     └─ pose_metrics.py
└─ shared/
   └─ schemas.py
```

## Example request

```json
{
  "current_landmarks": [
    { "x": 0.1, "y": 0.2, "z": 0.0 },
    { "x": 0.3, "y": 0.4, "z": 0.0 }
  ],
  "previous_landmarks": [
    { "x": 0.1, "y": 0.2, "z": 0.0 },
    { "x": 0.2, "y": 0.2, "z": 0.0 }
  ],
  "user_weight": 60,
  "elapsed_seconds": 1.5
}
```
