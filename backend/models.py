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


class AnalyzeResponse(BaseModel):
    highlights: list[Highlight]
    summary: str
    videoId: str


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


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
