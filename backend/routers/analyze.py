"""Analyze router for YOLO-based auto-highlight generation."""
import logging
import tempfile
from pathlib import Path
from fastapi import APIRouter, HTTPException

from models import AnalyzeResponse, AutoHighlightResult, Highlight
from services.storage import get_storage_service
from services.auto_highlight import get_auto_highlight_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/analyze/{video_id}", response_model=AnalyzeResponse)
async def analyze_video(video_id: str):
    storage = get_storage_service()
    highlight_service = get_auto_highlight_service()

    existing_analysis = storage.get_analysis(video_id)
    if existing_analysis and existing_analysis.get("autoHighlight"):
        logger.info(f"Returning cached analysis for {video_id}")
        reel_url = storage.get_reel_url(video_id)
        return AnalyzeResponse(
            highlights=existing_analysis.get("highlights", []),
            summary=existing_analysis.get("summary", ""),
            videoId=video_id,
            autoHighlight=existing_analysis.get("autoHighlight"),
            highlightVideoUrl=reel_url,
            highlightSignedUrl=reel_url,
        )

    if not storage.video_exists(video_id):
        raise HTTPException(status_code=404, detail="Video not found")

    logger.info(f"Starting YOLO auto-highlight analysis for video {video_id}")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = storage.download_video(video_id, tmpdir)
            output_path = str(Path(tmpdir) / "highlight.mp4")

            result = highlight_service.process_video(
                video_path=video_path,
                output_path=output_path,
            )

            # Store highlight video locally
            storage.upload_reel(video_id, output_path)
            reel_url = storage.get_reel_url(video_id)

            auto_result = AutoHighlightResult(
                targetPlayerId=result["target_id"],
                score=result["score"],
                signalTable=result["signal_table"],
                duration=result["duration"],
                frames=result["frames"],
                fps=result["fps"],
                resolution=result["resolution"],
                fileSizeMb=result["file_size_mb"],
            )

            highlight = Highlight(
                timestampSeconds=0,
                displayTime="0:00",
                description=f"Player #{result['target_id']} highlight reel - {result['duration']:.1f}s",
                scoreType="Highlight Reel",
                intensity="High",
                playerJerseyNumber=str(result["target_id"]),
            )

            summary = (
                f"Auto-generated highlight tracking Player #{result['target_id']} "
                f"(score: {result['score']:.3f}). "
                f"{result['duration']:.1f}s at {result['resolution']}."
            )

            analysis_dict = {
                "highlights": [highlight.model_dump()],
                "summary": summary,
                "autoHighlight": auto_result.model_dump(),
            }
            storage.upload_analysis(video_id, analysis_dict)

        logger.info(f"Analysis complete for {video_id}: target player #{result['target_id']}")

        return AnalyzeResponse(
            highlights=[highlight],
            summary=summary,
            videoId=video_id,
            autoHighlight=auto_result,
            highlightVideoUrl=reel_url,
            highlightSignedUrl=reel_url,
        )

    except RuntimeError as e:
        logger.error(f"Processing error: {e}")
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

    reel_url = storage.get_reel_url(video_id)

    return AnalyzeResponse(
        highlights=analysis.get("highlights", []),
        summary=analysis.get("summary", ""),
        videoId=video_id,
        autoHighlight=analysis.get("autoHighlight"),
        highlightVideoUrl=reel_url,
        highlightSignedUrl=reel_url,
    )
