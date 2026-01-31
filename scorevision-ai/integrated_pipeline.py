"""Unified pipeline combining AI analysis with highlight clipping."""
from __future__ import annotations

import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "highlight_mvp"))
sys.path.insert(0, str(Path(__file__).parent))

from ai_analyzer import analyze_video
from cache import load_cached, save_to_cache, get_cache_path
from converter import ai_to_scoresheet

logger = logging.getLogger(__name__)


def run_full_pipeline(
    video_path: str,
    output_dir: str,
    api_key: Optional[str] = None,
    use_cache: bool = True,
    pre_seconds: float = 6.0,
    post_seconds: float = 4.0,
    merge_gap_seconds: float = 2.0,
    min_clip_seconds: float = 2.0,
    max_clip_seconds: float = 30.0,
    make_reel: bool = True,
    analyze_only: bool = False,
) -> Dict[str, Any]:
    """
    Run the full AI + clipping pipeline.
    
    Pipeline steps:
    1. Check cache for AI analysis
    2. If not cached, call Gemini API
    3. Save to cache
    4. Convert to JSONL scoresheet
    5. Run clipping pipeline (unless analyze_only=True)
    6. Return manifest
    
    Args:
        video_path: Path to the source video file.
        output_dir: Directory for outputs.
        api_key: Gemini API key (or uses GEMINI_API_KEY env var).
        use_cache: Whether to use cached AI results.
        pre_seconds: Seconds before each event to include.
        post_seconds: Seconds after each event to include.
        merge_gap_seconds: Merge clips if gap is less than this.
        min_clip_seconds: Minimum clip duration.
        max_clip_seconds: Maximum clip duration.
        make_reel: Whether to create a highlight reel.
        analyze_only: If True, only analyze and cache, don't clip.
        
    Returns:
        Manifest dict with analysis and clip info.
    """
    logger.info("=" * 60)
    logger.info("ScoreVision AI + Clipping Pipeline")
    logger.info("=" * 60)
    
    video_path = str(Path(video_path).resolve())
    output_dir = str(Path(output_dir).resolve())
    
    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    logger.info(f"Video: {video_path}")
    logger.info(f"Output: {output_dir}")
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    logger.info("-" * 40)
    logger.info("Step 1: AI Analysis")
    
    ai_result = None
    cache_hit = False
    
    if use_cache:
        ai_result = load_cached(video_path)
        if ai_result:
            cache_hit = True
    
    if ai_result is None:
        logger.info("Running AI analysis...")
        ai_result = analyze_video(video_path, api_key=api_key)
        save_to_cache(video_path, ai_result)
    
    analysis_output = Path(output_dir) / "analysis.json"
    with open(analysis_output, "w", encoding="utf-8") as f:
        json.dump(ai_result, f, indent=2)
    logger.info(f"Analysis saved to: {analysis_output}")
    
    highlights = ai_result.get("highlights", [])
    logger.info(f"Found {len(highlights)} scoring events")
    
    if not highlights:
        logger.warning("No scoring events detected!")
        return {
            "video_path": video_path,
            "analysis": ai_result,
            "cache_hit": cache_hit,
            "num_events": 0,
            "clips": [],
            "reel": None,
        }
    
    logger.info("-" * 40)
    logger.info("Step 2: Generate Scoresheet")
    
    scoresheet_path = Path(output_dir) / "scoresheet.jsonl"
    ai_to_scoresheet(ai_result, str(scoresheet_path))
    
    if analyze_only:
        logger.info("=" * 60)
        logger.info("Analysis complete (--analyze-only mode)")
        logger.info("=" * 60)
        return {
            "video_path": video_path,
            "analysis": ai_result,
            "cache_hit": cache_hit,
            "scoresheet": str(scoresheet_path),
            "num_events": len(highlights),
        }
    
    logger.info("-" * 40)
    logger.info("Step 3: Generate Clips")
    
    try:
        from highlight_mvp.pipeline import generate_highlights
    except ImportError:
        from Clipping.pipeline import generate_highlights
    
    clip_manifest = generate_highlights(
        video_path=video_path,
        scoresheet_path=str(scoresheet_path),
        output_dir=output_dir,
        pre_seconds=pre_seconds,
        post_seconds=post_seconds,
        merge_gap_seconds=merge_gap_seconds,
        min_clip_seconds=min_clip_seconds,
        max_clip_seconds=max_clip_seconds,
        make_reel=make_reel,
    )
    
    full_manifest = {
        "video_path": video_path,
        "video_duration": clip_manifest.get("video_duration"),
        "analysis": ai_result,
        "cache_hit": cache_hit,
        "scoresheet": str(scoresheet_path),
        "num_events": len(highlights),
        "num_clips": clip_manifest.get("num_clips"),
        "clips": clip_manifest.get("clips"),
        "reel": clip_manifest.get("reel"),
    }
    
    manifest_path = Path(output_dir) / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(full_manifest, f, indent=2)
    
    logger.info("=" * 60)
    logger.info("Pipeline complete!")
    logger.info(f"  Events detected: {len(highlights)}")
    logger.info(f"  Clips generated: {clip_manifest.get('num_clips')}")
    logger.info(f"  Cache hit: {cache_hit}")
    logger.info(f"  Output: {output_dir}")
    logger.info("=" * 60)
    
    return full_manifest


def run_from_cache(
    video_path: str,
    output_dir: str,
    pre_seconds: float = 6.0,
    post_seconds: float = 4.0,
    merge_gap_seconds: float = 2.0,
    min_clip_seconds: float = 2.0,
    max_clip_seconds: float = 30.0,
    make_reel: bool = True,
) -> Dict[str, Any]:
    """
    Run clipping using only cached AI result (no API call).
    
    Raises:
        ValueError: If no cached result exists for this video.
    """
    ai_result = load_cached(video_path)
    
    if ai_result is None:
        raise ValueError(
            f"No cached analysis found for {Path(video_path).name}. "
            "Run with --no-cache-only first to analyze the video."
        )
    
    return run_full_pipeline(
        video_path=video_path,
        output_dir=output_dir,
        use_cache=True,
        pre_seconds=pre_seconds,
        post_seconds=post_seconds,
        merge_gap_seconds=merge_gap_seconds,
        min_clip_seconds=min_clip_seconds,
        max_clip_seconds=max_clip_seconds,
        make_reel=make_reel,
    )
