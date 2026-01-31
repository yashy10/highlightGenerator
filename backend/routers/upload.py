"""Upload router for video uploads to GCS."""
import logging
from fastapi import APIRouter, File, UploadFile, HTTPException

from models import UploadResponse
from services.storage import get_storage_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...)):
    storage = get_storage_service()
    
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only video files are accepted.",
        )
    
    video_id = storage.generate_video_id()
    
    logger.info(f"Uploading video {video_id}: {file.filename}")
    
    try:
        gcs_url = storage.upload_video(
            video_id=video_id,
            file=file.file,
            content_type=file.content_type,
            original_filename=file.filename or "original.mp4",
        )
        
        signed_url = storage.get_signed_url(gcs_url)
        
        logger.info(f"Video uploaded successfully: {video_id}")
        
        return UploadResponse(
            videoId=video_id,
            gcsUrl=gcs_url,
            signedUrl=signed_url,
        )
        
    except Exception as e:
        logger.exception(f"Failed to upload video: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload video: {str(e)}",
        )


@router.get("/videos/{video_id}")
async def get_video(video_id: str):
    storage = get_storage_service()
    
    if not storage.video_exists(video_id):
        raise HTTPException(status_code=404, detail="Video not found")
    
    gcs_url = storage.get_gcs_uri(video_id)
    if not gcs_url:
        raise HTTPException(status_code=404, detail="Video not found")
    
    signed_url = storage.get_signed_url(gcs_url)
    
    analysis = storage.get_analysis(video_id)
    has_analysis = analysis is not None
    
    clips = storage.list_clips(video_id)
    has_clips = len(clips) > 0
    
    return {
        "videoId": video_id,
        "gcsUrl": gcs_url,
        "signedUrl": signed_url,
        "analyzed": has_analysis,
        "hasClips": has_clips,
    }
