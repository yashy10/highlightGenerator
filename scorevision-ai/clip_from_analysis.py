#!/usr/bin/env python3
"""
Bridge script: Takes AI analysis JSON and generates clips using system FFmpeg.

Usage:
    # From exported analysis.json file:
    python clip_from_analysis.py --analysis analysis.json --video video.mp4 --out outputs/

    # From raw JSON string (for API/frontend integration):
    python clip_from_analysis.py --json '{"highlights":[...]}' --video video.mp4 --out outputs/
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "highlight_mvp"))

from converter import ai_to_scoresheet
from cache import save_to_cache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def clip_from_analysis(
    analysis: dict,
    video_path: str,
    output_dir: str,
    pre_seconds: float = 6.0,
    post_seconds: float = 4.0,
    merge_gap_seconds: float = 2.0,
    min_clip_seconds: float = 2.0,
    max_clip_seconds: float = 30.0,
    make_reel: bool = True,
    cache_analysis: bool = True,
) -> dict:
    """
    Generate clips from AI analysis using system FFmpeg.
    
    Args:
        analysis: AI analysis dict with 'highlights' array
        video_path: Path to the video file
        output_dir: Where to save clips
        pre_seconds: Seconds before each event
        post_seconds: Seconds after each event
        merge_gap_seconds: Merge clips if gap is less than this
        min_clip_seconds: Minimum clip duration
        max_clip_seconds: Maximum clip duration
        make_reel: Whether to create a highlight reel
        cache_analysis: Whether to cache the analysis for future use
        
    Returns:
        Manifest dict with clip info
    """
    video_path = str(Path(video_path).resolve())
    output_dir = str(Path(output_dir).resolve())
    
    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    highlights = analysis.get("highlights", [])
    logger.info(f"Processing {len(highlights)} highlights from analysis")
    
    if cache_analysis:
        save_to_cache(video_path, analysis)
        logger.info("Cached analysis for future use")
    
    analysis_path = Path(output_dir) / "analysis.json"
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)
    
    scoresheet_path = Path(output_dir) / "scoresheet.jsonl"
    ai_to_scoresheet(analysis, str(scoresheet_path))
    
    if not highlights:
        logger.warning("No highlights to clip!")
        return {
            "video_path": video_path,
            "num_events": 0,
            "clips": [],
            "reel": None,
        }
    
    try:
        from highlight_mvp.pipeline import generate_highlights
    except ImportError:
        from Clipping.pipeline import generate_highlights
    
    manifest = generate_highlights(
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
    
    manifest["analysis"] = analysis
    
    manifest_path = Path(output_dir) / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    
    logger.info(f"Generated {manifest['num_clips']} clips")
    if manifest.get("reel"):
        logger.info(f"Highlight reel: {output_dir}/{manifest['reel']}")
    
    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Generate clips from AI analysis JSON using system FFmpeg"
    )
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--analysis",
        type=str,
        help="Path to analysis.json file",
    )
    input_group.add_argument(
        "--json",
        type=str,
        help="Raw JSON string with analysis",
    )
    
    parser.add_argument(
        "--video",
        type=str,
        required=True,
        help="Path to the video file",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="outputs/clips",
        help="Output directory (default: outputs/clips)",
    )
    parser.add_argument("--pre", type=float, default=6.0)
    parser.add_argument("--post", type=float, default=4.0)
    parser.add_argument("--merge-gap", type=float, default=2.0)
    parser.add_argument("--make-reel", type=str, default="true")
    parser.add_argument("--no-cache", action="store_true")
    
    args = parser.parse_args()
    
    if args.analysis:
        with open(args.analysis, "r", encoding="utf-8") as f:
            analysis = json.load(f)
    else:
        analysis = json.loads(args.json)
    
    make_reel = args.make_reel.lower() in ("true", "1", "yes")
    
    try:
        manifest = clip_from_analysis(
            analysis=analysis,
            video_path=args.video,
            output_dir=args.out,
            pre_seconds=args.pre,
            post_seconds=args.post,
            merge_gap_seconds=args.merge_gap,
            make_reel=make_reel,
            cache_analysis=not args.no_cache,
        )
        
        print(f"\nClips saved to: {args.out}/clips/")
        if manifest.get("reel"):
            print(f"Highlight reel: {args.out}/{manifest['reel']}")
        
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
