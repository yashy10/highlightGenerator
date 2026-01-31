"""Gemini API service for video analysis."""
import json
import logging
from typing import Optional

import google.generativeai as genai

from config import get_settings
from models import AnalysisResult, Highlight

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


class GeminiService:
    def __init__(self):
        self.settings = get_settings()
        self._configured = False
    
    def _ensure_configured(self):
        if not self._configured:
            if not self.settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            genai.configure(api_key=self.settings.gemini_api_key)
            self._configured = True
    
    async def analyze_video_from_gcs(
        self,
        gcs_uri: str,
        model_name: str = "gemini-2.0-flash",
    ) -> AnalysisResult:
        self._ensure_configured()
        
        logger.info(f"Analyzing video from GCS: {gcs_uri}")
        
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_INSTRUCTION,
        )
        
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
        )
        
        video_file = genai.upload_file(gcs_uri)
        
        response = model.generate_content(
            [
                video_file,
                "Identify all scores and the jersey numbers of the scorers in JSON format."
            ],
            generation_config=generation_config,
        )
        
        result_text = response.text
        if not result_text:
            raise RuntimeError("Gemini returned an empty response")
        
        result = json.loads(result_text)
        
        highlights = [
            Highlight(
                timestampSeconds=h["timestampSeconds"],
                displayTime=h["displayTime"],
                description=h["description"],
                scoreType=h["scoreType"],
                intensity=h["intensity"],
                playerJerseyNumber=h.get("playerJerseyNumber", "Unknown"),
            )
            for h in result.get("highlights", [])
        ]
        
        logger.info(f"Analysis complete: {len(highlights)} highlights detected")
        
        return AnalysisResult(
            highlights=highlights,
            summary=result.get("summary", ""),
        )
    
    async def analyze_video_from_file(
        self,
        file_path: str,
        model_name: str = "gemini-2.0-flash",
    ) -> AnalysisResult:
        self._ensure_configured()
        
        logger.info(f"Analyzing video from file: {file_path}")
        
        video_file = genai.upload_file(file_path)
        
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_INSTRUCTION,
        )
        
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
        )
        
        response = model.generate_content(
            [
                video_file,
                "Identify all scores and the jersey numbers of the scorers in JSON format."
            ],
            generation_config=generation_config,
        )
        
        result_text = response.text
        if not result_text:
            raise RuntimeError("Gemini returned an empty response")
        
        result = json.loads(result_text)
        
        highlights = [
            Highlight(
                timestampSeconds=h["timestampSeconds"],
                displayTime=h["displayTime"],
                description=h["description"],
                scoreType=h["scoreType"],
                intensity=h["intensity"],
                playerJerseyNumber=h.get("playerJerseyNumber", "Unknown"),
            )
            for h in result.get("highlights", [])
        ]
        
        logger.info(f"Analysis complete: {len(highlights)} highlights detected")
        
        return AnalysisResult(
            highlights=highlights,
            summary=result.get("summary", ""),
        )


gemini_service = GeminiService()


def get_gemini_service() -> GeminiService:
    return gemini_service
