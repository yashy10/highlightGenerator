"""FFmpeg service for video clip generation."""
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FFmpegService:
    def __init__(self):
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError("FFmpeg not available")
            logger.info("FFmpeg is available")
        except FileNotFoundError:
            raise RuntimeError("FFmpeg not installed. Please install FFmpeg.")
    
    def get_video_duration(self, video_path: str) -> float:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "json",
                video_path,
            ],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to get video duration: {result.stderr}")
        
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    
    def cut_clip(
        self,
        video_path: str,
        output_path: str,
        start_seconds: float,
        duration_seconds: float,
        fast_seek: bool = True,
    ) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        if fast_seek:
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_seconds),
                "-i", video_path,
                "-t", str(duration_seconds),
                "-c", "copy",
                "-avoid_negative_ts", "make_zero",
                output_path,
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-ss", str(start_seconds),
                "-t", str(duration_seconds),
                "-c:v", "libx264",
                "-preset", "fast",
                "-c:a", "aac",
                output_path,
            ]
        
        logger.info(f"Cutting clip: {start_seconds}s - {start_seconds + duration_seconds}s")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            if fast_seek:
                logger.warning("Fast seek failed, retrying with re-encode...")
                return self.cut_clip(
                    video_path,
                    output_path,
                    start_seconds,
                    duration_seconds,
                    fast_seek=False,
                )
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")
        
        return output_path
    
    def generate_clips(
        self,
        video_path: str,
        highlights: list[dict],
        output_dir: str,
        pre_seconds: float = 6.0,
        post_seconds: float = 4.0,
    ) -> list[dict]:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        duration = self.get_video_duration(video_path)
        clips = []
        
        for i, highlight in enumerate(highlights):
            timestamp = highlight.get("timestampSeconds", 0)
            
            start = max(0, timestamp - pre_seconds)
            end = min(duration, timestamp + post_seconds)
            clip_duration = end - start
            
            output_path = str(Path(output_dir) / f"clip_{i:03d}.mp4")
            
            try:
                self.cut_clip(video_path, output_path, start, clip_duration)
                
                clips.append({
                    "index": i,
                    "start": start,
                    "end": end,
                    "path": output_path,
                    "highlight": highlight,
                })
                
                logger.info(f"Generated clip {i}: {start:.2f}s - {end:.2f}s")
                
            except Exception as e:
                logger.error(f"Failed to generate clip {i}: {e}")
        
        return clips
    
    def create_reel(
        self,
        clip_paths: list[str],
        output_path: str,
    ) -> str:
        if not clip_paths:
            raise ValueError("No clips to concatenate")
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for path in clip_paths:
                f.write(f"file '{path}'\n")
            concat_file = f.name
        
        try:
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                output_path,
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", concat_file,
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-c:a", "aac",
                    output_path,
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    raise RuntimeError(f"FFmpeg concat failed: {result.stderr}")
            
            logger.info(f"Created highlight reel: {output_path}")
            return output_path
            
        finally:
            Path(concat_file).unlink(missing_ok=True)


ffmpeg_service = FFmpegService()


def get_ffmpeg_service() -> FFmpegService:
    return ffmpeg_service
