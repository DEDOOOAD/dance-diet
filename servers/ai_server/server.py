from __future__ import annotations

from fastapi import FastAPI, UploadFile, File

from servers.ai_server.config import APP_NAME
from servers.ai_server.services.gif_pose_service import analyze_gif_file
from servers.ai_server.services.pose_metrics import analyze_pose_request
from servers.shared.schemas import GifAnalysisRequest, GifAnalysisResponse, PoseAnalysisRequest, PoseAnalysisResponse, ServerInfo, FoodAnalysisResponse, FoodAnalysisRequest
from servers.ai_server.services.food_pipeline import analyze_food_pipeline

app = FastAPI(
    title="AI Analysis API",
    version="1.0.0",
    description="AI server for pose and GIF analysis.",
)


@app.get("/health", response_model=ServerInfo)
def health() -> ServerInfo:
    return ServerInfo(name=APP_NAME, role="ai-server")


@app.post("/analyze/pose", response_model=PoseAnalysisResponse)
def analyze_pose(request: PoseAnalysisRequest) -> PoseAnalysisResponse:
    return analyze_pose_request(request)


@app.post("/analyze/gif", response_model=GifAnalysisResponse)
def analyze_gif(request: GifAnalysisRequest) -> GifAnalysisResponse:
    return analyze_gif_file(request)

@app.post("/food/analyze", response_model=FoodAnalysisResponse)
async def food_analyze(file: UploadFile = File(...)):
    return await analyze_food_pipeline(file)
