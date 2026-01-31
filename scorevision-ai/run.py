#!/usr/bin/env python3
"""CLI entry point for the AI-powered highlight generation pipeline."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from integrated_pipeline import run_full_pipeline, run_from_cache
from cache import list_cached, clear_cache, load_cached


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="scorevision",
        description="AI-powered sports highlight generator using Gemini + FFmpeg",
    )
    
    parser.add_argument(
        "--video",
        type=str,
        help="Path to the video file",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="outputs",
        help="Output directory (default: outputs)",
    )
    parser.add_argument(
        "--pre",
        type=float,
        default=6.0,
        help="Seconds before each event (default: 6.0)",
    )
    parser.add_argument(
        "--post",
        type=float,
        default=4.0,
        help="Seconds after each event (default: 4.0)",
    )
    parser.add_argument(
        "--merge-gap",
        type=float,
        default=2.0,
        help="Merge gap in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--min-clip",
        type=float,
        default=2.0,
        help="Minimum clip duration (default: 2.0)",
    )
    parser.add_argument(
        "--max-clip",
        type=float,
        default=30.0,
        help="Maximum clip duration (default: 30.0)",
    )
    parser.add_argument(
        "--make-reel",
        type=str,
        default="true",
        help="Create highlight reel (default: true)",
    )
    
    cache_group = parser.add_mutually_exclusive_group()
    cache_group.add_argument(
        "--no-cache",
        action="store_true",
        help="Force re-analyze, ignore cached results",
    )
    cache_group.add_argument(
        "--cache-only",
        action="store_true",
        help="Only use cached results, fail if not cached",
    )
    
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only run AI analysis, don't generate clips",
    )
    
    parser.add_argument(
        "--list-cache",
        action="store_true",
        help="List all cached analyses and exit",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear all cached analyses and exit",
    )
    parser.add_argument(
        "--show-cache",
        type=str,
        metavar="VIDEO",
        help="Show cached analysis for a video and exit",
    )
    
    parser.add_argument(
        "--api-key",
        type=str,
        help="Gemini API key (or set GEMINI_API_KEY env var)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    setup_logging(verbose=args.verbose)
    
    if args.list_cache:
        cached = list_cached()
        if not cached:
            print("No cached analyses found.")
            return 0
        print(f"Cached analyses ({len(cached)}):")
        for name, info in cached.items():
            print(f"  - {name}")
            print(f"      Cache file: {info.get('cache_file')}")
            print(f"      Cached at: {info.get('cached_at')}")
        return 0
    
    if args.clear_cache:
        count = clear_cache()
        print(f"Cleared {count} cached files.")
        return 0
    
    if args.show_cache:
        result = load_cached(args.show_cache)
        if result is None:
            print(f"No cached analysis found for: {args.show_cache}")
            return 1
        import json
        print(json.dumps(result, indent=2))
        return 0
    
    if not args.video:
        parser.error("--video is required (unless using --list-cache, --clear-cache, or --show-cache)")
    
    make_reel = args.make_reel.lower() in ("true", "1", "yes")
    
    try:
        if args.cache_only:
            manifest = run_from_cache(
                video_path=args.video,
                output_dir=args.out,
                pre_seconds=args.pre,
                post_seconds=args.post,
                merge_gap_seconds=args.merge_gap,
                min_clip_seconds=args.min_clip,
                max_clip_seconds=args.max_clip,
                make_reel=make_reel,
            )
        else:
            manifest = run_full_pipeline(
                video_path=args.video,
                output_dir=args.out,
                api_key=args.api_key,
                use_cache=not args.no_cache,
                pre_seconds=args.pre,
                post_seconds=args.post,
                merge_gap_seconds=args.merge_gap,
                min_clip_seconds=args.min_clip,
                max_clip_seconds=args.max_clip,
                make_reel=make_reel,
                analyze_only=args.analyze_only,
            )
        
        print(f"\nOutput saved to: {args.out}")
        if manifest.get("reel"):
            print(f"Highlight reel: {args.out}/{manifest['reel']}")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ImportError as e:
        print(f"Missing dependency: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"Runtime error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
