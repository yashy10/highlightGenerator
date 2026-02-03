"""Narration router - adds AI commentary to highlight videos."""
import logging
from fastapi import APIRouter, HTTPException

from models import NarrationResponse
from services.storage import get_storage_service
from services.narration import NarrationService

logger = logging.getLogger(__name__)

router = APIRouter()

_narration_service = None


def _get_narration_service() -> NarrationService:
    global _narration_service
    if _narration_service is None:
        _narration_service = NarrationService()
    return _narration_service


@router.post("/narrate/{video_id}", response_model=NarrationResponse)
async def narrate_highlight(video_id: str):
    """Add AI sports commentary narration to the highlight reel."""
    storage = get_storage_service()

    reel_path = storage.get_reel_path(video_id)
    if not reel_path:
        raise HTTPException(
            status_code=404,
            detail="No highlight reel found. Generate a highlight first.",
        )

    clips_dir = storage._clips_dir(video_id)
    output_path = str(clips_dir / "reel_narrated.mp4")

    try:
        service = _get_narration_service()
        service.add_narration(reel_path, output_path)
    except Exception as e:
        logger.exception("Narration failed")
        raise HTTPException(status_code=500, detail=f"Narration failed: {e}")

    narrated_url = f"/api/files/clips/{video_id}/reel_narrated.mp4"
    return NarrationResponse(videoId=video_id, narratedVideoUrl=narrated_url)
