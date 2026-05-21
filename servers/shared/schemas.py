from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, json, model_validator

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
    genre: str | None = None
    class_id: str | None = None

# Y
class LiveSessionStartResponse(BaseModel):
    session_id: str
    uuid: str
    status: str
    started_at: datetime
    transport: str = "websocket"
    stream_mode: str = "bidirectional"
    genre: str | None = None
    class_id: str | None = None
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

    type: Literal["frame_binary"] = "frame_binary"
    UUID: str
    session_id: str
    frame_index: int = Field(ge=0)
    total_frame: int = Field(ge=0)
    image: bytes
    user_weight: float

    @model_validator(mode="after")
    def validate_frame_payload(self) -> "LiveFrameMessage":
        if not self.image:
            raise ValueError("image(bytes payload) is required.")
        return self

    def get_frame_data(self) -> bytes:
        return self.image


class LiveFrameMessage_go_ai_server(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: Literal["frame_base64"] = "frame_base64"  
    UUID: str 
    session_id: str
    frame_index: int = Field(ge=0)
    total_frame: int = Field(ge=0)
    image: str
    user_weight: float

    @model_validator(mode="after")
    def validate_frame_payload(self) -> "LiveFrameMessage_go_ai_server":
        if not self.image:
            raise ValueError("image(base64 payload) is required.")
        return self

    def get_frame_data(self) -> str:
        return self.image

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


class DailyTallyRecord(BaseModel):
    user_id: str 
    summary_date: str
    total_burned_kcal: float = 0.0 
    total_duration_seconds: float = 0.0 
    session_count: int = 0  
    height: float | None = None 
    weight: float | None = None 
    target_weight: float | None = None 
    target_day: str | None = None  
    today_target_kcal: float | None = None 
    achievement_rate: float | None = None  


class YearlyRecordsResponse(BaseModel):
    uuid: str  
    year: int 
    days: list[DailyTallyRecord] = Field(default_factory=list) 


class MonthlyRecordsResponse(BaseModel):
    uuid: str  
    year: int 
    month: int 
    days: list[DailyTallyRecord] = Field(default_factory=list)  


class HalfYearWeightRecord(BaseModel):
    date_key: str
    year: int
    month: int
    avg_weight: float | None = None
    record_count: int = 0


class HalfYearWeightRecordsResponse(BaseModel):
    uuid: str
    year: int
    month: int
    weights: list[HalfYearWeightRecord] = Field(default_factory=list)
