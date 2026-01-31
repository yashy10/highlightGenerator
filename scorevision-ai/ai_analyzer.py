"""Gemini API client for video analysis."""
from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """
You are an elite sports broadcast analyst. 
Analyze the provided video and identify every significant scoring event.

For each event, you MUST identify:
1. timestampSeconds: The float timestamp of the score in seconds from video start.
2. displayTime: MM:SS format.
3. description: A 1-sentence exciting description.
4. scoreType: e.g. 'Goal', '3-Pointer', 'Touchdown', 'Try', 'Point'.
5. intensity: 'High', 'Medium', or 'Low'.
6. playerJerseyNumber: THE MOST IMPORTANT PART. Identify the jersey number of the player who scored. 
   Look closely at their back or chest during the celebration or the play. 
   Return just the number (e.g. "10", "7", "23"). 
   If absolutely impossible to see, return "Unknown".

Return the data strictly as a single JSON object.
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "highlights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "timestampSeconds": {"type": "number"},
                    "displayTime": {"type": "string"},
                    "description": {"type": "string"},
                    "scoreType": {"type": "string"},
                    "intensity": {"type": "string", "enum": ["High", "Medium", "Low"]},
                    "playerJerseyNumber": {"type": "string"}
                },
                "required": ["timestampSeconds", "displayTime", "description", "scoreType", "intensity", "playerJerseyNumber"]
            }
        },
        "summary": {"type": "string"}
    },
    "required": ["highlights", "summary"]
}


def analyze_video(
    video_path: str,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.0-flash",
) -> Dict[str, Any]:
    """
    Analyze a video using Gemini API to detect scoring events.
    
    Args:
        video_path: Path to the video file.
        api_key: Gemini API key. If not provided, uses GEMINI_API_KEY env var.
        model_name: The Gemini model to use.
        
    Returns:
        Dict with 'highlights' array and 'summary' string.
        
    Raises:
        ValueError: If no API key is provided.
        RuntimeError: If the API call fails.
    """
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError(
            "google-generativeai package not installed. Run:\n"
            "  pip install google-generativeai"
        )
    
    if api_key is None:
        api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError(
            "No API key provided. Either pass api_key argument or set GEMINI_API_KEY environment variable."
        )
    
    genai.configure(api_key=api_key)
    
    video_file = Path(video_path)
    if not video_file.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    file_size_mb = video_file.stat().st_size / (1024 * 1024)
    logger.info(f"Analyzing video: {video_file.name} ({file_size_mb:.1f} MB)")
    
    mime_type = _get_mime_type(video_file)
    logger.info(f"MIME type: {mime_type}")
    
    logger.info("Reading video file...")
    with open(video_file, "rb") as f:
        video_data = f.read()
    video_base64 = base64.b64encode(video_data).decode("utf-8")
    
    logger.info(f"Calling Gemini API ({model_name})...")
    
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=SYSTEM_INSTRUCTION,
    )
    
    generation_config = genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA,
    )
    
    try:
        response = model.generate_content(
            [
                {
                    "mime_type": mime_type,
                    "data": video_base64,
                },
                "Identify all scores and the jersey numbers of the scorers in JSON format."
            ],
            generation_config=generation_config,
        )
        
        result_text = response.text
        if not result_text:
            raise RuntimeError("The AI returned an empty response.")
        
        result = json.loads(result_text)
        
        highlights = result.get("highlights", [])
        logger.info(f"Analysis complete: {len(highlights)} scoring events detected")
        
        for i, h in enumerate(highlights):
            logger.info(f"  {i+1}. [{h.get('displayTime', '?')}] {h.get('scoreType', '?')} - {h.get('description', '')[:50]}...")
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        if "400" in error_msg:
            raise RuntimeError(
                "Video too large or format unsupported. Try a smaller clip or different format."
            )
        raise RuntimeError(f"Gemini API error: {error_msg}")


def _get_mime_type(file_path: Path) -> str:
    """Get MIME type based on file extension."""
    ext = file_path.suffix.lower()
    mime_types = {
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".webm": "video/webm",
        ".mkv": "video/x-matroska",
        ".m4v": "video/x-m4v",
    }
    return mime_types.get(ext, "video/mp4")


def query_video(
    video_path: str,
    query: str,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.0-flash",
) -> str:
    """
    Ask a free-form question about a video.
    
    Args:
        video_path: Path to the video file.
        query: The question to ask about the video.
        api_key: Gemini API key.
        model_name: The Gemini model to use.
        
    Returns:
        The AI's response as a string.
    """
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("google-generativeai package not installed.")
    
    if api_key is None:
        api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError("No API key provided.")
    
    genai.configure(api_key=api_key)
    
    video_file = Path(video_path)
    mime_type = _get_mime_type(video_file)
    
    with open(video_file, "rb") as f:
        video_data = f.read()
    video_base64 = base64.b64encode(video_data).decode("utf-8")
    
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction="You are an AI sports analyst. Be concise and helpful.",
    )
    
    response = model.generate_content([
        {
            "mime_type": mime_type,
            "data": video_base64,
        },
        query
    ])
    
    return response.text or "No response."
