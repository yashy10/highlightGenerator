"""Convert AI analysis output to JSONL scoresheet format."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def ai_to_scoresheet(ai_result: Dict[str, Any], output_path: str) -> str:
    """
    Convert Gemini AI analysis result to JSONL scoresheet format.
    
    Args:
        ai_result: The AI analysis result with 'highlights' array.
        output_path: Path to write the JSONL scoresheet.
        
    Returns:
        The path to the written scoresheet file.
        
    The output JSONL preserves AI metadata in extended format:
    {"t": 45.2, "event": "score", "scoreType": "Goal", "intensity": "High", ...}
    """
    highlights = ai_result.get("highlights", [])
    
    if not highlights:
        logger.warning("No highlights found in AI result")
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        for highlight in highlights:
            scoresheet_entry = _convert_highlight(highlight)
            f.write(json.dumps(scoresheet_entry) + "\n")
    
    logger.info(f"Wrote {len(highlights)} events to {output_path}")
    return str(output_file)


def _convert_highlight(highlight: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a single AI highlight to scoresheet format."""
    return {
        "t": highlight.get("timestampSeconds", 0),
        "event": "score",
        "displayTime": highlight.get("displayTime", ""),
        "scoreType": highlight.get("scoreType", ""),
        "intensity": highlight.get("intensity", "Medium"),
        "player": highlight.get("playerJerseyNumber", "Unknown"),
        "description": highlight.get("description", ""),
    }


def ai_to_timestamps(ai_result: Dict[str, Any]) -> List[float]:
    """
    Extract just the timestamps from AI result.
    
    Args:
        ai_result: The AI analysis result.
        
    Returns:
        List of timestamps in seconds.
    """
    highlights = ai_result.get("highlights", [])
    timestamps = [h.get("timestampSeconds", 0) for h in highlights]
    timestamps.sort()
    return timestamps


def scoresheet_to_ai_format(scoresheet_path: str) -> Dict[str, Any]:
    """
    Convert a JSONL scoresheet back to AI result format.
    
    Useful for loading cached scoresheets.
    
    Args:
        scoresheet_path: Path to the JSONL scoresheet.
        
    Returns:
        Dict in AI result format with 'highlights' array.
    """
    highlights = []
    
    with open(scoresheet_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            if entry.get("event") != "score":
                continue
            
            highlight = {
                "timestampSeconds": entry.get("t", 0),
                "displayTime": entry.get("displayTime", _seconds_to_display(entry.get("t", 0))),
                "description": entry.get("description", ""),
                "scoreType": entry.get("scoreType", "Score"),
                "intensity": entry.get("intensity", "Medium"),
                "playerJerseyNumber": entry.get("player", "Unknown"),
            }
            highlights.append(highlight)
    
    return {
        "highlights": highlights,
        "summary": f"Loaded {len(highlights)} events from scoresheet",
    }


def _seconds_to_display(seconds: float) -> str:
    """Convert seconds to MM:SS format."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def merge_ai_results(*results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple AI results into one, deduplicating by timestamp.
    
    Args:
        *results: Multiple AI result dicts.
        
    Returns:
        Merged result with deduplicated highlights.
    """
    all_highlights = []
    summaries = []
    
    for result in results:
        all_highlights.extend(result.get("highlights", []))
        if result.get("summary"):
            summaries.append(result["summary"])
    
    all_highlights.sort(key=lambda h: h.get("timestampSeconds", 0))
    
    deduplicated = []
    last_t = -1.0
    threshold = 0.35
    
    for h in all_highlights:
        t = h.get("timestampSeconds", 0)
        if t - last_t > threshold:
            deduplicated.append(h)
            last_t = t
    
    return {
        "highlights": deduplicated,
        "summary": " ".join(summaries) if summaries else "",
    }
