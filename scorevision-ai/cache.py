"""File-based cache for AI analysis results."""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / ".cache"


def _get_file_hash(file_path: str) -> str:
    """Generate a hash based on file path, size, and modification time."""
    path = Path(file_path)
    stat = path.stat()
    key = f"{path.name}-{stat.st_size}-{stat.st_mtime}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def get_cache_path(video_path: str) -> Path:
    """Get the cache file path for a video."""
    file_hash = _get_file_hash(video_path)
    return CACHE_DIR / f"{file_hash}.json"


def load_cached(video_path: str) -> Optional[Dict[str, Any]]:
    """
    Load cached analysis result if it exists.
    
    Returns:
        The cached analysis dict, or None if not cached.
    """
    cache_path = get_cache_path(video_path)
    
    if not cache_path.exists():
        logger.info(f"Cache miss for {Path(video_path).name}")
        return None
    
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cached = json.load(f)
        
        logger.info(f"Cache hit for {Path(video_path).name}")
        logger.info(f"  Cached at: {cached.get('cached_at', 'unknown')}")
        logger.info(f"  Highlights: {len(cached.get('result', {}).get('highlights', []))}")
        
        return cached.get("result")
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Invalid cache file, ignoring: {e}")
        return None


def save_to_cache(video_path: str, result: Dict[str, Any]) -> Path:
    """
    Save analysis result to cache.
    
    Args:
        video_path: Path to the video file.
        result: The AI analysis result dict.
        
    Returns:
        Path to the cache file.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    cache_path = get_cache_path(video_path)
    
    cache_entry = {
        "video_path": str(Path(video_path).resolve()),
        "video_name": Path(video_path).name,
        "cached_at": datetime.now().isoformat(),
        "result": result,
    }
    
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache_entry, f, indent=2)
    
    logger.info(f"Saved to cache: {cache_path.name}")
    _update_index(video_path, cache_path)
    
    return cache_path


def _update_index(video_path: str, cache_path: Path) -> None:
    """Update the index file mapping video names to cache files."""
    index_path = CACHE_DIR / "index.json"
    
    index = {}
    if index_path.exists():
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
        except json.JSONDecodeError:
            index = {}
    
    index[Path(video_path).name] = {
        "cache_file": cache_path.name,
        "full_path": str(Path(video_path).resolve()),
        "cached_at": datetime.now().isoformat(),
    }
    
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)


def list_cached() -> Dict[str, Any]:
    """List all cached analyses."""
    index_path = CACHE_DIR / "index.json"
    
    if not index_path.exists():
        return {}
    
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def clear_cache() -> int:
    """Clear all cached analyses. Returns number of files deleted."""
    if not CACHE_DIR.exists():
        return 0
    
    count = 0
    for file in CACHE_DIR.glob("*.json"):
        file.unlink()
        count += 1
    
    logger.info(f"Cleared {count} cached files")
    return count
