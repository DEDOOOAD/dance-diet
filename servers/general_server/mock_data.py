from __future__ import annotations

from copy import deepcopy
from typing import Any


APP_STATE: dict[str, Any] = {
    "user": {
        "id": "user-lee",
        "name": "LEE",
        "greeting": "안녕하세요",
        "avatar_text": "L",
        "subtitle": "K-POP 마니아 · 댄스 초심자",
        "weight_kg": 60,
        "daily_kcal_goal": 1950,
        "weekly_session_goal": 5,
    },
    "streak": {
        "current_days": 12,
        "title": "연속 댄스 달성",
        "subtitle": "오늘도 기록을 이어가 보세요",
    },
    "weekly_days": [
        {"name": "MON", "num": 10, "done": True},
        {"name": "TUE", "num": 11, "done": True},
        {"name": "WED", "num": 12, "done": True},
        {"name": "THU", "num": 13, "active": True},
        {"name": "FRI", "num": 14},
        {"name": "SAT", "num": 15},
        {"name": "SUN", "num": 16},
    ],
    "missions": [
        {"id": "mission-1", "genre": "K-POP", "name": "최신 K-POP 챌린지", "stars": "인기 급상승", "duration_minutes": 15, "kcal": 150, "icon": "music", "color": "#FF6B6B", "is_live": True},
        {"id": "mission-2", "genre": "HIP-HOP", "name": "힙합 유산소 파티", "stars": "고강도 추천", "duration_minutes": 30, "kcal": 300, "icon": "flash", "color": "#8B5CF6", "is_live": False},
        {"id": "mission-3", "genre": "LATIN", "name": "라틴 댄스 믹스", "stars": "중강도 추천", "duration_minutes": 20, "kcal": 200, "icon": "flame", "color": "#14B8A6", "is_live": False},
    ],
    "classes": [
        {"id": "class-1", "genre": "K-POP", "name": "HYBE 안무 마스터클래스", "instructor": "Min", "level": "중급", "duration_minutes": 45, "kcal": 320, "icon": "music", "color": "#FF6B6B", "students": 2841},
        {"id": "class-2", "genre": "HIP-HOP", "name": "리듬 타는 비트 파티", "instructor": "DJ Mochi", "level": "초급", "duration_minutes": 30, "kcal": 280, "icon": "flash", "color": "#8B5CF6", "students": 1594},
        {"id": "class-3", "genre": "LATIN", "name": "라틴 집중 코스", "instructor": "Sofia Luna", "level": "입문", "duration_minutes": 40, "kcal": 250, "icon": "flame", "color": "#14B8A6", "students": 987},
        {"id": "class-4", "genre": "JAZZ", "name": "재즈 스트레칭", "instructor": "Park Soo", "level": "입문", "duration_minutes": 25, "kcal": 180, "icon": "sparkles", "color": "#F59E0B", "students": 765},
        {"id": "class-5", "genre": "HOUSE", "name": "파워 하우스 루틴", "instructor": "Kwon Y", "level": "고급", "duration_minutes": 50, "kcal": 420, "icon": "fitness", "color": "#06B6D4", "students": 442},
        {"id": "class-6", "genre": "K-POP", "name": "아이돌 댄스 베이직", "instructor": "Hana", "level": "중급", "duration_minutes": 35, "kcal": 290, "icon": "star", "color": "#FF6B6B", "students": 3210},
    ],
    "records": {
        "weekly": {
            "stats": [
                {"label": "이번 주 소모", "value": 2560, "unit": "kcal", "icon": "flame", "color": "#FF6B6B"},
                {"label": "총 운동 시간", "value": 95, "unit": "분", "icon": "time", "color": "#8B5CF6"},
                {"label": "완료 세션", "value": 7, "unit": "회", "icon": "checkmark-circle", "color": "#14B8A6"},
                {"label": "연속 달성", "value": 12, "unit": "일", "icon": "trending-up", "color": "#F59E0B"},
            ],
            "chart": [
                {"day": "월", "kcal": 320},
                {"day": "화", "kcal": 580},
                {"day": "수", "kcal": 410},
                {"day": "목", "kcal": 1250, "active": True},
                {"day": "금", "kcal": 0},
                {"day": "토", "kcal": 0},
                {"day": "일", "kcal": 0},
            ],
        },
        "monthly": {
            "stats": [
                {"label": "이번 달 소모", "value": 12850, "unit": "kcal", "icon": "flame", "color": "#FF6B6B"},
                {"label": "총 운동 시간", "value": 640, "unit": "분", "icon": "time", "color": "#8B5CF6"},
                {"label": "완료 세션", "value": 41, "unit": "회", "icon": "checkmark-circle", "color": "#14B8A6"},
                {"label": "최장 연속", "value": 12, "unit": "일", "icon": "trending-up", "color": "#F59E0B"},
            ],
            "chart": [
                {"day": "1주", "kcal": 2240},
                {"day": "2주", "kcal": 3150},
                {"day": "3주", "kcal": 2980},
                {"day": "4주", "kcal": 4480, "active": True},
            ],
        },
        "history": [
            {"date": "오늘", "time": "18:30", "name": "최신 K-POP 챌린지", "kcal": 150, "duration_minutes": 15, "icon": "music", "color": "#FF6B6B"},
            {"date": "오늘", "time": "10:00", "name": "힙합 유산소 파티", "kcal": 300, "duration_minutes": 30, "icon": "flash", "color": "#8B5CF6"},
            {"date": "어제", "time": "20:00", "name": "라틴 댄스 믹스", "kcal": 200, "duration_minutes": 20, "icon": "flame", "color": "#14B8A6"},
            {"date": "어제", "time": "09:15", "name": "HYBE 안무 마스터클래스", "kcal": 320, "duration_minutes": 45, "icon": "music", "color": "#FF6B6B"},
            {"date": "3일 전", "time": "21:00", "name": "리듬 타는 비트 파티", "kcal": 280, "duration_minutes": 30, "icon": "flash", "color": "#8B5CF6"},
        ],
    },
    "achievements": [
        {"id": "ach-1", "icon": "flame", "title": "12일 연속", "sub": "스트릭 마스터", "unlocked": True, "color": "#FF6B6B"},
        {"id": "ach-2", "icon": "ribbon", "title": "100회 운동", "sub": "운동 달인", "unlocked": True, "color": "#8B5CF6"},
        {"id": "ach-3", "icon": "trophy", "title": "고강도 10회", "sub": "칼로리 파이터", "unlocked": True, "color": "#F59E0B"},
        {"id": "ach-4", "icon": "rocket", "title": "1만 kcal", "sub": "칼로리 버너", "unlocked": False, "color": "#9CA3AF"},
        {"id": "ach-5", "icon": "moon", "title": "야간 운동왕", "sub": "자정 이후 5회", "unlocked": False, "color": "#9CA3AF"},
        {"id": "ach-6", "icon": "albums", "title": "장르 마스터", "sub": "5가지 장르 완료", "unlocked": False, "color": "#9CA3AF"},
    ],
    "settings": {
        "goals": {"daily_kcal_goal": 1950, "weekly_session_goal": 5, "weight_kg": 60},
        "toggles": {"workout_reminder": False, "dark_mode": True, "auto_music": True},
        "menu": [
            {"title": "목표 & 건강", "items": [{"icon": "body-outline", "label": "몸무게 & 목표 설정", "arrow": True}, {"icon": "nutrition-outline", "label": "칼로리 목표", "value": "1,950 kcal", "arrow": True}, {"icon": "barbell-outline", "label": "주간 목표 세션", "value": "5회", "arrow": True}]},
            {"title": "앱 설정", "items": [{"icon": "notifications-outline", "label": "운동 리마인더", "toggle_key": "workout_reminder"}, {"icon": "moon-outline", "label": "다크 모드", "toggle_key": "dark_mode"}, {"icon": "musical-notes-outline", "label": "음악 자동 재생", "toggle_key": "auto_music"}]},
            {"title": "기타", "items": [{"icon": "share-social-outline", "label": "친구에게 공유", "arrow": True}, {"icon": "star-outline", "label": "앱 평가하기", "arrow": True}, {"icon": "help-circle-outline", "label": "도움말 & 지원", "arrow": True}]},
        ],
    },
}


def clone_state() -> dict[str, Any]:
    return deepcopy(APP_STATE)
