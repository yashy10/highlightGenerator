"""Narration service - adds AI sports commentary to highlight videos."""
import time
import subprocess
import json
import tempfile
import logging
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from google import genai
from openai import OpenAI

logger = logging.getLogger(__name__)


class NarrationService:
    def __init__(self):
        self.gemini_client = genai.Client()
        self.openai_client = OpenAI()

    def _get_video_duration(self, video_path: str) -> float:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
        except (KeyError, ValueError, json.JSONDecodeError):
            logger.error(f"Failed to get duration for {video_path}")
            return 0.0

    def _describe_video(self, video_path: str) -> str:
        logger.info("Uploading video to Gemini...")
        myfile = self.gemini_client.files.upload(file=video_path)

        while myfile.state.name == "PROCESSING":
            time.sleep(2)
            myfile = self.gemini_client.files.get(name=myfile.name)

        logger.info("Generating description...")
        response = self.gemini_client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[myfile, "describe this video in detail."],
        )
        return response.text

    def _generate_script(self, description: str, duration: float) -> str:
        word_limit = max(5, int(duration * 2.5))
        prompt = f"""
Narrate this video in an exciting way.
Use a sports commentator's style.
The video is VERY SHORT, only {duration:.2f} seconds long.
The script MUST be less than {word_limit} words to fit within the time.
Do not include any scene directions, just the spoken text.

Description:
{description}
"""
        completion = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional sports commentator."},
                {"role": "user", "content": prompt},
            ],
        )
        return completion.choices[0].message.content

    def _generate_audio(self, script: str, output_path: str) -> None:
        with self.openai_client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="coral",
            input=script,
        ) as response:
            response.stream_to_file(output_path)

    def _mux_video_audio(self, video_path: str, audio_path: str, output_path: str) -> None:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", audio_path,
                "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac",
                "-shortest",
                output_path,
            ],
            check=True,
            capture_output=True,
        )

    def add_narration(self, video_path: str, output_path: str) -> str:
        """Run the full narration pipeline on a video and save the result."""
        duration = self._get_video_duration(video_path)
        if duration <= 0:
            raise RuntimeError("Could not determine video duration")

        description = self._describe_video(video_path)
        script = self._generate_script(description, duration)
        logger.info(f"Generated script: {script}")

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            audio_path = tmp.name

        self._generate_audio(script, audio_path)
        self._mux_video_audio(video_path, audio_path, output_path)

        Path(audio_path).unlink(missing_ok=True)
        return output_path
