"""Upload router for video uploads."""
import logging
from fastapi import APIRouter, File, UploadFile, HTTPException

from models import UploadResponse
from services.storage import get_storage_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...)):
    print("Received file upload request")  # Debugging statement
    storage = get_storage_service()
    print("Storage service initialized")  # Debugging statement

    if not file.content_type or not file.content_type.startswith("video/"):
        print(f"Invalid file type: {file.content_type}")  # Debugging statement
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only video files are accepted.",
        )

    video_id = storage.generate_video_id()
    print(f"Generated video ID: {video_id}")  # Debugging statement

    logger.info(f"Uploading video {video_id}: {file.filename}")

    try:
        file_path = storage.upload_video(
            video_id=video_id,
            file=file.file,
            content_type=file.content_type,
            original_filename=file.filename or "original.mp4",
        )
        print(f"Video uploaded successfully to path: {file_path}")  # Debugging statement

        logger.info(f"Video uploaded successfully: {video_id}")

        return UploadResponse(
            videoId=video_id,
            gcsUrl=file_path,
            signedUrl=f"/api/files/uploads/{video_id}/original.mp4",
        )

    except Exception as e:
        print(f"Exception occurred during upload: {e}")  # Debugging statement
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

    video_path = storage.get_video_path(video_id)
    analysis = storage.get_analysis(video_id)
    clips = storage.list_clips(video_id)

    return {
        "videoId": video_id,
        "videoPath": video_path,
        "analyzed": analysis is not None,
        "hasClips": len(clips) > 0,
    }
