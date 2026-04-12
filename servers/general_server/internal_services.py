from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from servers.general_server.socket_manager.ai_outbound import analyze_food_with_ai
from servers.shared import db_connect
from servers.shared.Bucket import FOOD_BUCKET, PROFILE_BUCKET
from servers.shared.schemas import FoodIntakeAnalysisResponse, UserProfileUpdate, UserSignUp


LOGGER = logging.getLogger(__name__)
db = db_connect.db_connect()

SYNCED_SIGNUP_COLUMNS = {"Name", "Email", "Password", "Age"}
SYNCED_PROFILE_COLUMNS = {"Height", "Weight", "Target_weight", "created_at", "Target_day", "Today_Target_kcal", "Current_streak", "Bucket_Profile_Photo", "FilePath"}
SUPPORTED_IMAGE_EXTENSIONS = {".webp", ".bmp", ".jpg", ".jpeg", ".png"}


def build_storage_public_url(bucket: str | None, path: str | None) -> str | None:
    if not bucket or not path:
        return None

    return db.storage.from_(bucket).get_public_url(path)


def raise_upstream_error(error: Exception) -> None:
    message = str(error)
    if "PGRST002" in message or "Error 521" in message or "Web server is down" in message:
        raise HTTPException(status_code=503, detail="Supabase is temporarily unavailable. Please try again later.",)

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


# 하루 섭취 칼로리 총합 계산            db에서 가져와서 계산하는 걸로 바꿔야함*****************************************************************
def calculate_total_intake_calories(uuid: str, day: str) -> float:
    return get_food_record(uuid, day).get("TotalCalories", 0.0)


# 이 부분은 테스트를 위해서 임시로 임식 데이터를 넣은거고 ai server에서 분석 받는 걸로 리턴하도록 검토 예정
def build_mock_food_intake_analysis(filename: str | None = None) -> dict[str, object]:
    mock_foods = [{"label": "bibimbap", "calories": 560.0, "confidence": 0.97}, 
                  {"label": "kimchi", "calories": 35.0, "confidence": 0.99}, 
                  {"label": "fried_egg", "calories": 90.0, "confidence": 0.95}]

    return {"foods": mock_foods, "total_calories": round(sum(food["calories"] for food in mock_foods), 1), "image_filename": filename, "source": "mock-general-server", "analyzed_at": datetime.now().astimezone(), "note": "Mock response. Replace this with the AI server food analysis result later.",}


async def analyze_food_intake_mock(image: UploadFile) -> dict[str, object]:
    return build_mock_food_intake_analysis(image.filename)


# 이건 사용자가 프로필 설정에서 세부 목표를 입력 했을때 사용함
def build_home_payload(uuid: str) -> dict[str, object]:
    user_profile = get_profile_record(uuid)
    today = datetime.now().date().isoformat()
    daily_target_burn_kcal = calculate_daily_target_kcal(user_profile.get("Weight"), user_profile.get("Target_weight"), user_profile.get("Target_day"),)
    daily_intake_kcal = calculate_total_intake_calories(uuid=uuid, day=today)

    return {"uuid": uuid, "day": today, "daily_target_burn_kcal": daily_target_burn_kcal, "today_target_kcal": daily_target_burn_kcal, "target_kcal": daily_target_burn_kcal, "daily_intake_kcal": daily_intake_kcal, "today_intake_kcal": daily_intake_kcal, "intake_kcal": daily_intake_kcal, "current_streak": user_profile.get("Current_streak"),}


# 이건 서버가 대충 넣어둬야하는 부분
def build_classes_payload(genre: str | None, search: str | None) -> bool:
    return True


# 기록이 있어야하는지 모르겠는데 아마 지우지 않을까하는 함수
def build_records_payload(period: str) -> bool:
    return True


def build_daily_food_intake_payload(uuid: str, year: int, month: int, day: int) -> dict[str, object]:
    date_str = f"{year:04d}-{month:02d}-{day:02d}"
    return get_food_record(uuid, date_str)


# 수정 끝
def build_profile_payload(uuid: str) -> dict[str, object]:
    user_profile = get_profile_record(uuid)
    profile_image_url = build_storage_public_url(user_profile.get("Bucket_Profile_Photo"), user_profile.get("FilePath"),)

    return {"uuid": user_profile["UUID"], "name": user_profile["Name"], "email": user_profile["Email"], "age": user_profile["Age"], "password": user_profile["Password"], "created_at": user_profile["Created_at"], "height": user_profile["Height"], "weight": user_profile["Weight"], "target_weight": user_profile["Target_weight"], "target_day": user_profile["Target_day"], "target_kcal": user_profile["Today_Target_kcal"], "today_target_kcal": user_profile["Today_Target_kcal"], "bucket_profile_photo": user_profile["Bucket_Profile_Photo"], "filepath": user_profile["FilePath"], "profile_image_url": profile_image_url, "current_streak": user_profile["Current_streak"],}


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


def create_signup_record(user: UserSignUp) -> str | bool:
    uuid = str(uuid4())
    signup_data = {"UUID": uuid, "Name": user.name, "Email": user.email, "Password": user.password, "Age": user.age, "Created_at": datetime.now().isoformat(),}

    try:
        response = db.table("SignUp").insert(signup_data).execute()
        if not response:
            raise HTTPException(status_code=500, detail="Failed to create user")

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


def update_user_record(uuid: str, user: UserProfileUpdate, image: UploadFile) -> bool:
    try:
        update_data = build_profile_update_data(user)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_profile_image(uuid, image)
        update_signup = {key: update_data[key] for key in SYNCED_SIGNUP_COLUMNS if key in update_data}
        update_profile = {key: update_data[key] for key in SYNCED_PROFILE_COLUMNS if key in update_data}

        response_signup = db.table("SignUp").update(update_signup).eq("UUID", uuid).execute() if update_signup else None
        response_pro = db.table("Profile").update(update_profile).eq("UUID", uuid).execute() if update_profile else None

        signup_rows = response_signup.data if response_signup else []
        profile_rows = response_pro.data if response_pro else []

        if not signup_rows and not profile_rows:
            raise HTTPException(status_code=404, detail="Profile not found")

        return True
    except HTTPException:
        return False
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
        payload = await analyze_food_with_ai(uuid, image_bytes, image.filename)
    except HTTPException as error:
        LOGGER.warning("Food AI analysis failed uuid=%s detail=%s", uuid, getattr(error, "detail", str(error)))
        payload = FoodIntakeAnalysisResponse.model_validate(build_mock_food_intake_analysis(image.filename))


    # 지금 ai 서버를 거치든 아니든 무조건 db에 넣는 상태라서 오류는 뜨지만 insert는 되는 중
    if insert_daily_food_log_rows(uuid, record_time, payload, storage_path) == False:
        return FoodIntakeAnalysisResponse(foods=payload.foods, total_calories=payload.total_calories, image_filename=payload.image_filename or image.filename, source=payload.source, analyzed_at=payload.analyzed_at, note="Failed",)

    return FoodIntakeAnalysisResponse(foods=payload.foods, total_calories=payload.total_calories, image_filename=payload.image_filename or image.filename, source=payload.source, analyzed_at=payload.analyzed_at, note=payload.note,)
