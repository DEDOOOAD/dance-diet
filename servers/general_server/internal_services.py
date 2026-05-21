from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from servers.shared import db_connect
from servers.shared.Bucket import FOOD_BUCKET, PROFILE_BUCKET
from servers.shared.schemas import FoodIntakeAnalysisResponse, MonthlyRecordsResponse, UserProfileUpdate, UserSignUp, YearlyRecordsResponse
from servers.general_server.videos.get_video import search_videos_api
from servers.general_server.food_analysis import analysis_request


LOGGER = logging.getLogger(__name__)
db = db_connect.db_connect()

SYNCED_SIGNUP_COLUMNS = {"Name", "Email", "Password", "Age"}
SYNCED_PROFILE_COLUMNS = {"Height", "Weight", "Target_weight", "created_at", "Target_day", "Today_Target_kcal", 
                          "Current_streak", "Bucket_Profile_Photo", "FilePath"}
SUPPORTED_IMAGE_EXTENSIONS = {".webp", ".bmp", ".jpg", ".jpeg", ".png"}
PROFILE_PENDING_IMAGE_NAME = "__pending_profile_image__"


def build_pending_profile_storage_path(uuid: str) -> str:
    return f"{uuid}/{PROFILE_PENDING_IMAGE_NAME}"

def yearly_records(uuid: str, year: int) -> YearlyRecordsResponse:
    rows = db.table("tally_table").select("*").eq("user_id", uuid).gte("summary_date", date_format(year)).lt("summary_date", date_format(year + 1)).order("summary_date").execute().data or []  # 해당 연도 범위에 포함되는 일간 집계 row를 날짜순으로 조회합니다.
    return YearlyRecordsResponse(uuid=uuid, year=year, days=rows) 

def monthly_records(uuid: str, year: int, month: int) -> MonthlyRecordsResponse:
    next_year, next_month = next_month_start(year, month)  
    rows = db.table("tally_table").select("*").eq("user_id", uuid).gte("summary_date", date_format(year, month)).lt("summary_date", date_format(next_year, next_month)).order("summary_date").execute().data or []  # 해당 월 범위에 포함되는 일간 집계 row를 날짜순으로 조회합니다.
    return MonthlyRecordsResponse(uuid=uuid, year=year, month=month, days=rows)

def next_month_start(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)

def date_format(year: int, month: int = 1, day: int = 1) -> str:
    return f"{year:04d}-{month:02d}-{day:02d}"  

def is_pending_profile_storage_path(path: str | None) -> bool:
    return bool(path) and path.endswith(f"/{PROFILE_PENDING_IMAGE_NAME}")


def build_storage_public_url(bucket: str | None, path: str | None) -> str | None:
    if not bucket or not path or is_pending_profile_storage_path(path):
        return None

    return db.storage.from_(bucket).get_public_url(path)

def raise_upstream_error(error: Exception) -> None:
    message = str(error)
    if "PGRST002" in message or "Error 521" in message or "Web server is down" in message:
        raise HTTPException(status_code=503, detail="Supabase is temporarily unavailable. Please try again later.",)
    if "23505" in message and "profile_bucket_path_key" in message:
        raise HTTPException(status_code=409, detail="Signup failed because the Profile table already contains a duplicate default profile image path. Keep Bucket_Profile_Photo as Profile_Photo, and change the signup-side Profile default or trigger to use a UUID-based placeholder FilePath instead of the shared empty path.",)

    raise HTTPException(status_code=500, detail=message)


def validate_supported_image_upload(image: UploadFile) -> None:
    filename = image.filename or ""
    extension = Path(filename).suffix.lower()

    if extension in SUPPORTED_IMAGE_EXTENSIONS:
        return

    content_type = (image.content_type or "").lower()
    content_type_extension_map = {"image/webp": ".webp", "image/bmp": ".bmp", "image/x-ms-bmp": ".bmp", "image/jpeg": ".jpg", "image/png": ".png"}
    if content_type in content_type_extension_map:
        return

    raise HTTPException(status_code=400, detail="Unsupported image type. Allowed types: webp, bmp, jpg, jpeg, png.")


def resolve_supported_image_extension(image: UploadFile) -> str:
    extension = Path(image.filename or "").suffix.lower()

    if extension in SUPPORTED_IMAGE_EXTENSIONS:
        return extension

    content_type = (image.content_type or "").lower()
    content_type_extension_map = {"image/webp": ".webp", "image/bmp": ".bmp", "image/x-ms-bmp": ".bmp", "image/jpeg": ".jpg", "image/png": ".png"}
    return content_type_extension_map.get(content_type, "")

def login_user(Email: str, password:str) -> bool:
        try: 
            response = db.rpc("Find_Register", {"p_email" : Email, "p_password" : password}).execute()
            logging.info("Login response: %s", response)
        except Exception as error:
            raise_upstream_error(error)

        return response

def get_profile_record(uuid: str) -> dict[str, Any]:
    try:
        result = db.table("Profile").select("*, signup:SignUp(Name, Email, Age, Password, Created_at)").eq("UUID", uuid).limit(1).execute().data
    except Exception as error:
        raise_upstream_error(error)

    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")

    record = result[0]
    signup_record = record.pop("signup", None)

    if isinstance(signup_record, list):
        signup_record = signup_record[0] if signup_record else None

    if isinstance(signup_record, dict):
        record["Name"] = signup_record.get("Name")
        record["Email"] = signup_record.get("Email")
        record["Age"] = signup_record.get("Age")
        record["Password"] = signup_record.get("Password")
        record["Created_at"] = signup_record.get("Created_at")

    return record


def get_signup_record(uuid: str) -> dict[str, Any]:
    try:
        rows = db.table("SignUp").select("UUID, Name, Email, Age, Created_at").eq("UUID", uuid).limit(1).execute().data
    except Exception as error:
        raise_upstream_error(error)

    if not rows:
        raise HTTPException(status_code=404, detail="Signup user not found")

    return rows[0]


def isexist_signup(uuid: str) -> bool:
    try:
        rows = db.table("SignUp").select("UUID").eq("UUID", uuid).limit(1).execute().data
    except Exception as error:
        raise_upstream_error(error)

    return bool(rows)


def build_food_storage_path(uuid: str, extension: str, day: datetime) -> str:
    return f"{uuid}/{day.strftime('%Y%m%d_%H%M%S')}_{uuid4().hex}{extension}"


def insert_daily_food_log_rows(uuid: str, day_value: datetime, analysis: FoodIntakeAnalysisResponse, file_path: str) -> bool:
    rows = [{"UUID": uuid, "Day": day_value.date().isoformat(), "FoodName": food.label, "Calories": float(food.calories), "Bucket_Name": FOOD_BUCKET, "File_Path": file_path} for food in analysis.foods]

    if not rows:
        exception = Exception("No food items to log")
        LOGGER.error("Failed to build food log rows: %s", exception)     
        return False                                      

    try:
        db.table("DailyFoodLog").insert(rows).execute()
        return True
    except Exception as error:
        raise_upstream_error(error)
        return False


def get_food_record(uuid: str, day: str) -> dict[str, Any]:
    try:
        rows = db.table("DailyFoodLog").select("FoodName, Calories, Bucket_Name, File_Path").eq("UUID", uuid).eq("Day", day).execute().data
    except Exception as error:
        raise_upstream_error(error)

    if not rows:
        return {"UUID": uuid, "Day": day, "Foods": [], "TotalCalories": 0.0, "RecordCount": 0}

    foods: list[dict[str, Any]] = []
    total_calories = 0.0

    for row in rows:
        try:
            calories = float(row.get("Calories") or 0.0)
        except (TypeError, ValueError):
            calories = 0.0

        normalized_row = dict(row)
        normalized_row["Calories"] = calories
        normalized_row["image_url"] = build_storage_public_url(row.get("Bucket_Name"), row.get("File_Path"))
        foods.append(normalized_row)
        total_calories += calories

    return {"UUID": uuid, "Day": day, "Foods": foods, "TotalCalories": round(total_calories, 1), "RecordCount": len(foods)}


# 하루 목표 소모 칼로리 계산
def calculate_daily_target_kcal(current_weight: float | None, target_weight: float | None, target_day: datetime | str | None, *, reference_date: datetime | None = None, kcal_per_kg: float = 7700.0, maximum_daily_kcal: float = 1500.0) -> float:
    if current_weight is None or target_weight is None or target_day is None:
        return 0.0

    try:
        current_weight_value = float(current_weight)
        target_weight_value = float(target_weight)
    except (TypeError, ValueError):
        return 0.0

    if isinstance(target_day, str):
        try:
            target_day = datetime.fromisoformat(target_day)
        except ValueError:
            return 0.0

    if not isinstance(target_day, datetime):
        return 0.0

    weight_gap = current_weight_value - target_weight_value
    if weight_gap <= 0:
        return 0.0

    reference = reference_date or datetime.now(tz=target_day.tzinfo)
    days_remaining = max(1, (target_day.date() - reference.date()).days)
    required_kcal = (weight_gap * kcal_per_kg) / days_remaining

    return round(min(required_kcal, maximum_daily_kcal), 1)


# 하루 음식 칼로리 총합 계산
def calculate_total_intake_calories(uuid: str, day: str) -> float:
    return get_food_record(uuid, day).get("TotalCalories", 0.0)


# 사용자가 프로필 설정에서 목표를 입력했을 때 사용하는 홈 화면 데이터입니다.
def build_home_payload(uuid: str) -> dict[str, object]:
    user_profile = get_profile_record(uuid)
    today = datetime.now().date().isoformat()
    daily_target_burn_kcal = calculate_daily_target_kcal(user_profile.get("Weight"), user_profile.get("Target_weight"), user_profile.get("Target_day"),)
    daily_intake_kcal = calculate_total_intake_calories(uuid=uuid, day=today)

    return {"uuid": uuid, "day": today, "daily_target_burn_kcal": daily_target_burn_kcal, "today_target_kcal": daily_target_burn_kcal, "target_kcal": daily_target_burn_kcal, "daily_intake_kcal": daily_intake_kcal, "today_intake_kcal": daily_intake_kcal, "intake_kcal": daily_intake_kcal, "current_streak": user_profile.get("Current_streak"),}


def search_classes(search: str | None) -> dict[str, object]:

    result = search_videos(search)
    if result.get("total_results", 0) == 0:
        api_result = search_videos_api(search)
        insert_videos(api_result)
        return api_result
    
    return result

def insert_videos(api_result: dict | None) -> dict[str, object]:
    for video in api_result.get("videos", []):    
        db.rpc("Insert_Videos", { 
            "p_videoid": video["video_id"],
            "p_title": video["title"],
            "p_description": video["description"],
            "p_duration": video["duration_seconds"],
            "p_tag": video["tags"]
       }).execute()

def search_videos(search: str | None) -> dict[str, object]:     
    result = db.rpc("Search_Videos", {"p_search" : search}).execute()

    if not result.data:
        return {"videos": [], "total_results": 0}

    return {"videos": result.data, "total_results": len(result.data)}
    




def build_daily_food_intake_payload(uuid: str, year: int, month: int, day: int) -> dict[str, object]:
    date_str = f"{year:04d}-{month:02d}-{day:02d}"
    return get_food_record(uuid, date_str)


def build_profile_payload(uuid: str) -> dict[str, object]:
    user_profile = get_profile_record(uuid)
    filepath = user_profile.get("FilePath")
    has_profile_image = bool(filepath) and not is_pending_profile_storage_path(filepath)
    bucket_profile_photo = user_profile.get("Bucket_Profile_Photo") if has_profile_image else None
    profile_image_url = build_storage_public_url(bucket_profile_photo, filepath if has_profile_image else None,)

    return {"uuid": user_profile["UUID"], "name": user_profile["Name"], "email": user_profile["Email"], "age": user_profile["Age"], "password": user_profile["Password"], "created_at": user_profile["Created_at"], "height": user_profile["Height"], "weight": user_profile["Weight"], "target_weight": user_profile["Target_weight"], "target_day": user_profile["Target_day"], "target_kcal": user_profile["Today_Target_kcal"], "today_target_kcal": user_profile["Today_Target_kcal"], "bucket_profile_photo": bucket_profile_photo, "filepath": filepath if has_profile_image else None, "profile_image_url": profile_image_url, "current_streak": user_profile["Current_streak"],}


def build_profile_update_data(user: UserProfileUpdate) -> dict[str, Any]:
    payload = user.model_dump(mode="json", exclude_none=True)
    field_map = {"name": "Name", "email": "Email", "password": "Password", "age": "Age", "created_at": "Created_at", "height": "Height", "weight": "Weight", "target_weight": "Target_weight", "target_day": "Target_day", "today_target_kcal": "Today_Target_kcal", "current_streak": "Current_streak", "bucket_profile_photo": "Bucket_Profile_Photo", "filepath": "FilePath"}
    
    return {field_map[key]: value for key, value in payload.items()}


def update_profile_image(uuid: str, image: UploadFile) -> str:
    validate_supported_image_upload(image)
    ext = resolve_supported_image_extension(image)
    path = f"{uuid}/{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    image.file.seek(0)
    response = db.storage.from_(PROFILE_BUCKET).upload(path=path, file=image.file, file_options={"cache-control": "3600", "upsert": "false",},)
    LOGGER.info("Upload response: %s", response)

    return path


def normalize_signup_profile_image_path(uuid: str) -> None:
    try:
        db.table("Profile").update({"Bucket_Profile_Photo": PROFILE_BUCKET, "FilePath": build_pending_profile_storage_path(uuid)}).eq("UUID", uuid).eq("Bucket_Profile_Photo", PROFILE_BUCKET).eq("FilePath", "").execute()
    except Exception as error:
        LOGGER.warning("Failed to normalize auto-created Profile image path for signup uuid=%s error=%s", uuid, error)


def create_signup_record(user: UserSignUp) -> str | bool:
    uuid = str(uuid4())
    signup_data = {"UUID": uuid, "Name": user.name, "Email": user.email, "Password": user.password, "Age": user.age, "Created_at": datetime.now().isoformat(),}

    try:
        response = db.table("SignUp").insert(signup_data).execute()
        if not response:
            raise HTTPException(status_code=500, detail="Failed to create user")

        normalize_signup_profile_image_path(uuid)
        return uuid
    except HTTPException:
        return False
    except Exception as error:
        raise_upstream_error(error)


def delete_user_record(uuid: str) -> bool:
    try:
        profile_response = db.table("Profile").delete().eq("UUID", uuid).execute()
        if not profile_response.data:
            raise HTTPException(status_code=404, detail="User not found")

        return True
    except HTTPException:
        return False
    except Exception as error:
        raise_upstream_error(error)



def update_user_record(uuid: str, user: UserProfileUpdate, image: UploadFile | None) -> bool:
    try:
        update_data = build_profile_update_data(user)

        if image:
            path = update_profile_image(uuid, image)
            update_data["FilePath"] = path
            update_data["Bucket_Profile_Photo"] = PROFILE_BUCKET

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_signup = {key: update_data[key] for key in SYNCED_SIGNUP_COLUMNS if key in update_data}
        update_profile = {key: update_data[key] for key in SYNCED_PROFILE_COLUMNS if key in update_data}

        if update_signup:
            db.table("SignUp").update(update_signup).eq("UUID", uuid).execute()

        existing = db.table("Profile").select("UUID").eq("UUID", uuid).limit(1).execute().data

        if existing:
            db.table("Profile").update(update_profile).eq("UUID", uuid).execute()
        else:
            insert_data = {"UUID": uuid, **update_profile}
            db.table("Profile").insert(insert_data).execute()

        return True

    except Exception as error:
        raise_upstream_error(error)


def update_user_prototype_record(uuid: str, form_payload: dict[str, Any], image: UploadFile | None) -> dict[str, Any] | bool:
    try:
        prototype_field_map = {"name": "Name", "email": "Email", "password": "Password", "age": "Age", "created_at": "Created_at", "height": "Height", "weight": "Weight", "target_weight": "Target_weight", "target_day": "Target_day", "today_target_kcal": "Today_Target_kcal", "current_streak": "Current_streak"}
        update_data = {prototype_field_map[key]: value.isoformat() if isinstance(value, datetime) else value for key, value in form_payload.items() if value is not None}

        uploaded_path = None
        if image is not None:
            validate_supported_image_upload(image)
            ext = resolve_supported_image_extension(image)
            uploaded_path = f"{uuid}/{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            image.file.seek(0)
            contents = image.file.read()
            db.storage.from_(PROFILE_BUCKET).upload(path=uploaded_path, file=contents, file_options={"cache-control": "3600", "upsert": "false", "content-type": image.content_type or "application/octet-stream",},)
            update_data["Bucket_Profile_Photo"] = PROFILE_BUCKET
            update_data["FilePath"] = uploaded_path

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_signup = {key: update_data[key] for key in SYNCED_SIGNUP_COLUMNS if key in update_data}
        update_profile = {key: update_data[key] for key in SYNCED_PROFILE_COLUMNS if key in update_data}

        response_signup = db.table("SignUp").update(update_signup).eq("UUID", uuid).execute() if update_signup else None
        response_pro = db.table("Profile").update(update_profile).eq("UUID", uuid).execute() if update_profile else None

        signup_rows = response_signup.data if response_signup else []
        profile_rows = response_pro.data if response_pro else []

        if not signup_rows and not profile_rows:
            raise HTTPException(status_code=404, detail="Profile not found")

        return {"ok": True, "uploaded_path": uploaded_path, "profile_image_url": build_storage_public_url(PROFILE_BUCKET, uploaded_path) if uploaded_path else None,}
    except HTTPException:
        return False
    except Exception as error:
        raise_upstream_error(error)


async def process_food_intake_request(uuid: str, day: datetime | None, image: UploadFile) -> FoodIntakeAnalysisResponse:
    if not isexist_signup(uuid):
        raise HTTPException(status_code=404, detail="User not found")

    validate_supported_image_upload(image)
    extension = resolve_supported_image_extension(image)

    image_bytes = await image.read()
    record_time = day or datetime.now().astimezone()
    storage_path = build_food_storage_path(uuid, extension, record_time)

    try:
        db.storage.from_(FOOD_BUCKET).upload(path=storage_path, file=image_bytes, file_options={"cache-control": "3600", "upsert": "false", "content-type": image.content_type or "application/octet-stream",},)
    except Exception as error:
        raise_upstream_error(error)

    try:
        payload = await analysis_request(uuid, image_bytes, image.filename)
    except HTTPException as error:
        LOGGER.warning("Food AI analysis failed uuid=%s detail=%s", uuid, getattr(error, "detail", str(error)))

        return FoodIntakeAnalysisResponse(
            foods=[],
            total_calories=0.0,
            image_filename=image.filename,
            source="ai-food-server",
            analyzed_at=datetime.now().astimezone(),
            note="Failed",
        )

    if insert_daily_food_log_rows(uuid, record_time, payload, storage_path) == False:
        return FoodIntakeAnalysisResponse(foods=payload.foods, total_calories=payload.total_calories, image_filename=payload.image_filename or image.filename, source=payload.source, analyzed_at=payload.analyzed_at, note="Failed",)

    return FoodIntakeAnalysisResponse(foods=payload.foods, total_calories=payload.total_calories, image_filename=payload.image_filename or image.filename, source=payload.source, analyzed_at=payload.analyzed_at, note=payload.note,)


def save_session_data(session: dict[str, Any]) -> None:
    try:

        summary_date = session.get("started_at").date()
        day_start = datetime.combine(summary_date, datetime.min.time(), tzinfo=session["started_at"].tzinfo)
        day_end = day_start + timedelta(days=1)

        insert_exercise_session(session)

        exist_today_pre_sessions = db.table("tally_table").select("*").eq("user_id", session.get("uuid")).eq("summary_date", summary_date.isoformat()).execute()
        res = db.table("exercise_sessions").select("*").eq("user_id", session.get("uuid")).gte("started_at", day_start.isoformat()).lt("started_at", day_end.isoformat()).execute()
        
        if len(exist_today_pre_sessions.data or []) != 0:
            update_tally_table(session, res, summary_date.isoformat())
        elif len(res.data or []) != 0:
            insert_tally_table(session)
        

    except Exception as error:
        LOGGER.error("Failed to save session data for uuid=%s error=%s", session.get("uuid"), error)

def insert_tally_table(session):

    user_profile = select_profile(session)

    db.table("tally_table").insert({
        "user_id": session.get("uuid"),
        "summary_date": session.get("started_at").date().isoformat(),
        "total_burned_kcal": session.get("total_calories", 0.0),
        "total_duration_seconds": session.get("elapsed_seconds", 0),
        "session_count": 1,
        "height": user_profile[0].get("Height") if user_profile else None,
        "weight":  user_profile[0].get("Weight") if user_profile else None,
        "target_weight": user_profile[0].get("Target_weight") if user_profile else None,
        "target_day": user_profile[0].get("Target_day") if user_profile else None,
        "today_target_kcal": user_profile[0].get("Today_Target_kcal") if user_profile else None,
        "achievement_rate": session.get("total_calories", 0) / (user_profile[0].get("Today_Target_kcal") or 1) * 100 if user_profile else None,
    }).execute()

    
def select_profile(session):
    res = db.table("Profile").select("*").eq("UUID", session.get("uuid")).execute()

    return res.data or []

def update_tally_table(session, res, summary_date):
    db.table("tally_table").update({
        "total_burned_kcal": sum(item.get("burned_kcal", 0) for item in res.data or []),
        "total_duration_seconds": sum(item.get("duration_seconds", 0) for item in res.data or []),
        "session_count": len(res.data or []),
        "achievement_rate": sum(item.get("burned_kcal", 0) for item in res.data or []) / (select_profile(session)[0].get("Today_Target_kcal") or 1) * 100 if select_profile(session) else None,
        }).eq("user_id", session.get("uuid")).eq("summary_date", summary_date).execute()

def insert_exercise_session(session):
    db.table("exercise_sessions").insert({
            "session_id": session["session_id"],
            "user_id": session.get("uuid"), 
            "class_id": session["class_id"], 
            "started_at": session["started_at"].isoformat(), 
            "ended_at": session["ended_at"].isoformat(),
            "duration_seconds": session["elapsed_seconds"], 
            "burned_kcal": session["total_calories"],
        }).execute()
