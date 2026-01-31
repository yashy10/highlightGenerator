"""Analyze router for AI video analysis."""
import logging
import tempfile
from pathlib import Path
from fastapi import APIRouter, HTTPException

from models import AnalyzeResponse
from services.storage import get_storage_service
from services.gemini import get_gemini_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/analyze/{video_id}", response_model=AnalyzeResponse)
async def analyze_video(video_id: str):
    storage = get_storage_service()
    gemini = get_gemini_service()
    
    existing_analysis = storage.get_analysis(video_id)
    if existing_analysis:
        logger.info(f"Returning cached analysis for {video_id}")
        return AnalyzeResponse(
            highlights=existing_analysis.get("highlights", []),
            summary=existing_analysis.get("summary", ""),
            videoId=video_id,
        )
    
    gcs_uri = storage.get_gcs_uri(video_id)
    if not gcs_uri:
        raise HTTPException(status_code=404, detail="Video not found")
    
    logger.info(f"Starting analysis for video {video_id}")
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = storage.download_video(video_id, tmpdir)
            
            result = await gemini.analyze_video_from_file(video_path)
        
        analysis_dict = {
            "highlights": [h.model_dump() for h in result.highlights],
            "summary": result.summary,
        }
        storage.upload_analysis(video_id, analysis_dict)
        
        logger.info(f"Analysis complete for {video_id}: {len(result.highlights)} highlights")
        
        return AnalyzeResponse(
            highlights=result.highlights,
            summary=result.summary,
            videoId=video_id,
        )
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error analyzing video: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/analyze/{video_id}", response_model=AnalyzeResponse)
async def get_analysis(video_id: str):
    storage = get_storage_service()
    
    analysis = storage.get_analysis(video_id)
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found. Run POST /api/analyze/{video_id} first.",
        )
    
    return AnalyzeResponse(
        highlights=analysis.get("highlights", []),
        summary=analysis.get("summary", ""),
        videoId=video_id,
    )
