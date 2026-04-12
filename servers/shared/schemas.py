from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Y
class UserSignUp(BaseModel):
    name: str
    email: str
    password: str
    age: int
    created_at: datetime

# Y
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

# Y
class LiveSessionStartRequest(BaseModel):
    uuid: str
    dance_type: str | None = None
    content_id: str | None = None

# Y
class LiveSessionStartResponse(BaseModel):
    session_id: str
    uuid: str
    status: str
    started_at: datetime
    transport: str = "websocket"
    stream_mode: str = "bidirectional"
    dance_type: str | None = None
    content_id: str | None = None
    ws_url: str

# Y
class LiveSessionEndRequest(BaseModel):
    session_id: str

# Y
class LiveSessionEndResponse(BaseModel):
    session_id: str
    status: str
    ended_at: datetime
    total_frames: int
    elapsed_seconds: float
    total_calories: float
    message: str

# Y
class LiveFrameMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: Literal["frame"] = "frame"
    UUID: str 
    session_id: str
    frame_index: int = Field(ge=0)
    total_frame: int = Field(ge=0)
    image_base64: str
    user_weight: float = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_frame_payload(self) -> "LiveFrameMessage":
        if not self.image_base64:
            raise ValueError("One of image_base64 is required.")
        return self

    def get_frame_data(self) -> str:
        if self.image_base64:
            return self.image_base64

        raise ValueError("Frame payload is missing.")

# Y
class AiLiveAnalysisMessage(BaseModel):
    type: Literal["ai_analysis"] = "ai_analysis"
    session_id: str
    processed_at: datetime
    calories_burned: float = 0.0
    movement_score: float = 0.0

# Y
class LiveFrameResultMessage(BaseModel):
    type: Literal["frame_result"] = "frame_result"
    session_id: str
    frame_index: int = Field(ge=0)
    total_frames: int = Field(ge=0)
    elapsed_seconds: float = 0.0
    accepted: bool = True
    calories_burned: float = 0.0
    total_calories: float = 0.0
    movement_score: float = 0.0
    processed_at: datetime | None = None
    message: str | None = None

# ************************* FOOD ****************************
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
