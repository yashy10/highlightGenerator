"""FastAPI application for ScoreVision AI backend."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routers import upload, analyze, clips
from models import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("ScoreVision AI Backend starting...")
    yield
    print("ScoreVision AI Backend shutting down...")


app = FastAPI(
    title="ScoreVision AI API",
    description="Video highlight detection and clip generation API",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(clips.router, prefix="/api", tags=["clips"])


@app.get("/", response_model=HealthResponse)
async def root():
    return HealthResponse(
        status="ok",
        service="ScoreVision AI API",
        version="1.0.0",
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        service="ScoreVision AI API",
        version="1.0.0",
    )
