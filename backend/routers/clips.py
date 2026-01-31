"""Clips router for video clip generation."""
import logging
import tempfile
from pathlib import Path
from fastapi import APIRouter, HTTPException

from models import ClipsRequest, ClipsResponse, ClipInfo
from services.storage import get_storage_service
from services.ffmpeg import get_ffmpeg_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/clips/{video_id}", response_model=ClipsResponse)
async def generate_clips(video_id: str, request: ClipsRequest):
    storage = get_storage_service()
    ffmpeg = get_ffmpeg_service()
    
    if not storage.video_exists(video_id):
        raise HTTPException(status_code=404, detail="Video not found")
    
    analysis = storage.get_analysis(video_id)
    if not analysis:
        raise HTTPException(
            status_code=400,
            detail="Video not analyzed yet. Run POST /api/analyze/{video_id} first.",
        )
    
    highlights = analysis.get("highlights", [])
    if not highlights:
        return ClipsResponse(clips=[], videoId=video_id)
    
    logger.info(f"Generating {len(highlights)} clips for video {video_id}")
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = storage.download_video(video_id, tmpdir)
            
            clips_dir = Path(tmpdir) / "clips"
            clips_dir.mkdir(parents=True, exist_ok=True)
            
            local_clips = ffmpeg.generate_clips(
                video_path=video_path,
                highlights=highlights,
                output_dir=str(clips_dir),
                pre_seconds=request.preSeconds,
                post_seconds=request.postSeconds,
            )
            
            clip_infos = []
            clip_paths = []
            
            for clip in local_clips:
                gcs_url = storage.upload_clip(
                    video_id=video_id,
                    file_path=clip["path"],
                    clip_index=clip["index"],
                )
                
                signed_url = storage.get_signed_url(gcs_url)
                clip_paths.append(clip["path"])
                
                clip_infos.append(ClipInfo(
                    url=gcs_url,
                    signedUrl=signed_url,
                    start=clip["start"],
                    end=clip["end"],
                    index=clip["index"],
                ))
            
            reel_url = None
            reel_signed_url = None
            
            if request.makeReel and clip_paths:
                reel_path = str(Path(tmpdir) / "reel.mp4")
                ffmpeg.create_reel(clip_paths, reel_path)
                
                reel_url = storage.upload_reel(video_id, reel_path)
                reel_signed_url = storage.get_signed_url(reel_url)
            
            manifest = {
                "videoId": video_id,
                "numClips": len(clip_infos),
                "clips": [c.model_dump() for c in clip_infos],
                "reelUrl": reel_url,
            }
            storage.upload_manifest(video_id, manifest)
            
            logger.info(f"Generated {len(clip_infos)} clips for {video_id}")
            
            return ClipsResponse(
                clips=clip_infos,
                reelUrl=reel_url,
                reelSignedUrl=reel_signed_url,
                videoId=video_id,
            )
            
    except Exception as e:
        logger.exception(f"Failed to generate clips: {e}")
        raise HTTPException(status_code=500, detail=f"Clip generation failed: {str(e)}")


@router.get("/clips/{video_id}", response_model=ClipsResponse)
async def get_clips(video_id: str):
    storage = get_storage_service()
    
    if not storage.video_exists(video_id):
        raise HTTPException(status_code=404, detail="Video not found")
    
    clip_urls = storage.list_clips(video_id)
    
    clip_infos = []
    for i, gcs_url in enumerate(sorted(clip_urls)):
        signed_url = storage.get_signed_url(gcs_url)
        clip_infos.append(ClipInfo(
            url=gcs_url,
            signedUrl=signed_url,
            start=0,
            end=0,
            index=i,
        ))
    
    reel_url = storage.get_reel_url(video_id)
    reel_signed_url = storage.get_signed_url(reel_url) if reel_url else None
    
    return ClipsResponse(
        clips=clip_infos,
        reelUrl=reel_url,
        reelSignedUrl=reel_signed_url,
        videoId=video_id,
    )
