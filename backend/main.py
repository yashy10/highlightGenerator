"""FastAPI application for auto-highlight backend."""
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from config import get_settings
from routers import upload, analyze, clips, narration
from models import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Auto-Highlight Backend starting...")
    yield
    print("Auto-Highlight Backend shutting down...")


app = FastAPI(
    title="Auto-Highlight API",
    description="YOLO-based player tracking and highlight generation API",
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
app.include_router(narration.router, prefix="/api", tags=["narration"])


@app.get("/api/files/{file_path:path}")
async def serve_file(file_path: str):
    """Serve locally stored video/clip files."""
    full_path = Path(settings.storage_dir) / file_path
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(full_path), media_type="video/mp4")


@app.get("/", response_model=HealthResponse)
async def root():
    return HealthResponse(
        status="ok",
        service="Auto-Highlight API",
        version="1.0.0",
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        service="Auto-Highlight API",
        version="1.0.0",
    )
