import base64
from servers.general_server.config import AI_HOST, AI_PORT, AI_FOOD_API_PATH
from servers.shared.schemas import FoodAnalysisRequest, FoodIntakeAnalysisResponse
from fastapi import HTTPException
import httpx

def build_food_api_url():
    return f"http://{AI_HOST}:{AI_PORT}{AI_FOOD_API_PATH}"

async def analysis_request(uuid: str, image_bytes: bytes, image_filename: str | None) -> FoodIntakeAnalysisResponse:
    request_data = FoodAnalysisRequest(
        uuid=uuid, 
        image_filename=image_filename,
        image_base64=base64.b64encode(image_bytes).decode("ascii")).model_dump(mode="json")

    async with httpx.AsyncClient() as client:
        try: 
            response = await client.post(build_food_api_url(), json=request_data, timeout=30.0)
            response.raise_for_status()
            response_data = response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"AI server request failed: {exc}") from exc
        
    return FoodIntakeAnalysisResponse(**response_data)
