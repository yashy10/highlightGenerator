"""Pydantic models for request/response validation."""
from typing import Optional
from pydantic import BaseModel


class Highlight(BaseModel):
    timestampSeconds: float
    displayTime: str
    description: str
    scoreType: str
    intensity: str
    playerJerseyNumber: Optional[str] = "Unknown"


class AnalysisResult(BaseModel):
    highlights: list[Highlight]
    summary: str


class UploadResponse(BaseModel):
    videoId: str
    gcsUrl: str
    signedUrl: str
    duration: Optional[float] = None


class AnalyzeRequest(BaseModel):
    pass


class AutoHighlightResult(BaseModel):
    targetPlayerId: int
    score: float
    signalTable: dict[str, float]
    duration: float
    frames: int
    fps: float
    resolution: str
    fileSizeMb: float


class AnalyzeResponse(BaseModel):
    highlights: list[Highlight]
    summary: str
    videoId: str
    autoHighlight: Optional[AutoHighlightResult] = None
    highlightVideoUrl: Optional[str] = None
    highlightSignedUrl: Optional[str] = None


class ClipsRequest(BaseModel):
    preSeconds: float = 6.0
    postSeconds: float = 4.0
    makeReel: bool = True


class ClipInfo(BaseModel):
    url: str
    signedUrl: str
    start: float
    end: float
    index: int


class ClipsResponse(BaseModel):
    clips: list[ClipInfo]
    reelUrl: Optional[str] = None
    reelSignedUrl: Optional[str] = None
    videoId: str


class VideoInfo(BaseModel):
    videoId: str
    gcsUrl: str
    signedUrl: str
    uploadedAt: str
    analyzed: bool
    hasClips: bool


class NarrationResponse(BaseModel):
    videoId: str
    narratedVideoUrl: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
