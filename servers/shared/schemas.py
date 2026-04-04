from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# normal schemas
class ServerInfo(BaseModel):
    name: str
    role: str
    status: str = "ok"

class UserSignUp(BaseModel):
    name: str
    email: str
    password: str
    age: int
    created_at: datetime

class UserProfileUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    password: str | None = None
    age: int | None = None
    created_at: datetime 
    weight: float | None = None
    height: float | None = None
    target_weight: float | None = None
    target_day: datetime | None = None
    today_target_kcal: float | None = None
    current_streak: int | None = None
    bucket_profile_photo: str | None = None
    filepath: str | None = None

class GeneralAiProxyResponse(BaseModel):
    ai_server_url: str
    recommended_endpoints: list[str]
    note: str

# session schemas
class LiveSessionStartRequest(BaseModel):
    user_id: str
    dance_type: str | None = None
    content_id: str | None = None

class LiveSessionStartResponse(BaseModel):
    session_id: str
    user_id: str
    status: str
    started_at: datetime
    ws_url: str
    dance_type: str | None = None
    content_id: str | None = None

class LiveSessionEndRequest(BaseModel):
    session_id: str

class LiveSessionEndResponse(BaseModel):
    session_id: str
    status: str
    ended_at: datetime
    total_frames: int
    elapsed_seconds: float
    total_calories: float
    message: str


class PosePoint(BaseModel):
    x: float
    y: float
    z: float = 0.0

class PoseAnalysisRequest(BaseModel):
    current_landmarks: list[PosePoint] = Field(default_factory=list)
    previous_landmarks: list[PosePoint] = Field(default_factory=list)
    user_weight: float = 60.0
    elapsed_seconds: float = 1.0

class PoseAnalysisResponse(BaseModel):
    movement_score: float
    current_met: float
    calories_burned: float
    landmark_count: int


# Food Schemas
class FoodItem(BaseModel):
    label: str
    calories: float
    confidence: float

class FoodAnalysisResponse(BaseModel):
    foods: list[FoodItem]

class FoodIntakeAnalysisResponse(BaseModel):
    foods: list[FoodItem]
    total_calories: float
    image_filename: str | None = None
    source: str
    analyzed_at: datetime
    note: str | None = None

class FoodRecordItem(BaseModel):
    UUID: str
    Day: str
    FoodName: str | None = None
    Calories: float = 0.0

class FoodRecordResponse(BaseModel):
    UUID: str
    Day: str
    Foods: list[FoodRecordItem] = Field(default_factory=list)
    TotalCalories: float = 0.0
    RecordCount: int = 0

class FoodAnalysisRequest(BaseModel):
    uuid: str
    image_base64: str
