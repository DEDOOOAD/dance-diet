import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

from servers.general_server.config import GET_TAG_URL, SEARCH_URL

BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def youtube_api_token() -> str:
    return _required_env("YOUTUBE_API_TOKEN")

def get_http_with_requests(url, params):
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def parse_youtube_duration_seconds(duration: str | None):
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration or "")
    if not match:
        return None

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds

def search_video_ids(query, max_results=100):

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": min(max_results, 50),
        "key": youtube_api_token()
    }

    data = get_http_with_requests(SEARCH_URL, params)

    video_ids = []
    for item in data.get("items", []):
        vid = item.get("id", {}).get("videoId")
        if vid:
            video_ids.append(vid)

    return video_ids


def get_video_details(video_ids):
    if not video_ids:
        return []

    params = {
        "part": "snippet,contentDetails",
        "id": ",".join(video_ids),
        "key": youtube_api_token()
    }

    data = get_http_with_requests(GET_TAG_URL, params)

    results = []

    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        content_details = item.get("contentDetails", {})
        duration_seconds = parse_youtube_duration_seconds(content_details.get("duration"))

        if duration_seconds is None or duration_seconds < 120:
            continue

        results.append({
            "video_id": item.get("id"),
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "duration_seconds": duration_seconds,
            "tags": snippet.get("tags", [])
        })

    return results


def search_videos_api(query, max_results=100):
    
    video_ids = search_video_ids(query, max_results)
    videos = get_video_details(video_ids)

    return {"videos": videos}
