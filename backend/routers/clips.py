"""Clips router - returns the generated highlight video."""
import logging
from fastapi import APIRouter, HTTPException

from models import ClipsRequest, ClipsResponse, ClipInfo
from services.storage import get_storage_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/clips/{video_id}", response_model=ClipsResponse)
async def generate_clips(video_id: str, request: ClipsRequest):
    """Returns the auto-generated highlight video as a single clip."""
    storage = get_storage_service()

    if not storage.video_exists(video_id):
        raise HTTPException(status_code=404, detail="Video not found")

    analysis = storage.get_analysis(video_id)
    if not analysis:
        raise HTTPException(
            status_code=400,
            detail="Video not analyzed yet. Run POST /api/analyze/{video_id} first.",
        )

    reel_url = storage.get_reel_url(video_id)
    if not reel_url:
        return ClipsResponse(clips=[], videoId=video_id)

    auto_highlight = analysis.get("autoHighlight", {})
    duration = auto_highlight.get("duration", 0)

    clip_info = ClipInfo(
        url=reel_url,
        signedUrl=reel_url,
        start=0,
        end=duration,
        index=0,
    )

    return ClipsResponse(
        clips=[clip_info],
        reelUrl=reel_url,
        reelSignedUrl=reel_url,
        videoId=video_id,
    )


@router.get("/clips/{video_id}", response_model=ClipsResponse)
async def get_clips(video_id: str):
    storage = get_storage_service()

    if not storage.video_exists(video_id):
        raise HTTPException(status_code=404, detail="Video not found")

    reel_url = storage.get_reel_url(video_id)
    if not reel_url:
        return ClipsResponse(clips=[], videoId=video_id)

    analysis = storage.get_analysis(video_id)
    auto_highlight = (analysis or {}).get("autoHighlight", {})
    duration = auto_highlight.get("duration", 0)

    clip_info = ClipInfo(
        url=reel_url,
        signedUrl=reel_url,
        start=0,
        end=duration,
        index=0,
    )

    return ClipsResponse(
        clips=[clip_info],
        reelUrl=reel_url,
        reelSignedUrl=reel_url,
        videoId=video_id,
    )
