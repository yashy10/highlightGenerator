"""Local file storage service for video and clip management."""
import json
import uuid
import shutil
from pathlib import Path
from typing import Optional, BinaryIO

from config import get_settings


class StorageService:
    def __init__(self):
        self.settings = get_settings()
        self.base_dir = Path(self.settings.storage_dir)
        self.uploads_dir = self.base_dir / "uploads"
        self.clips_dir = self.base_dir / "clips"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.clips_dir.mkdir(parents=True, exist_ok=True)

    def generate_video_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def _video_dir(self, video_id: str) -> Path:
        return self.uploads_dir / video_id

    def _clips_dir(self, video_id: str) -> Path:
        return self.clips_dir / video_id

    def upload_video(
        self,
        video_id: str,
        file: BinaryIO,
        content_type: str = "video/mp4",
        original_filename: str = "original.mp4",
    ) -> str:
        ext = Path(original_filename).suffix or ".mp4"
        video_dir = self._video_dir(video_id)
        video_dir.mkdir(parents=True, exist_ok=True)
        dest = video_dir / f"original{ext}"
        with open(dest, "wb") as f:
            shutil.copyfileobj(file, f)
        return str(dest)

    def upload_analysis(self, video_id: str, analysis: dict) -> str:
        video_dir = self._video_dir(video_id)
        video_dir.mkdir(parents=True, exist_ok=True)
        dest = video_dir / "analysis.json"
        dest.write_text(json.dumps(analysis, indent=2))
        return str(dest)

    def get_analysis(self, video_id: str) -> Optional[dict]:
        path = self._video_dir(video_id) / "analysis.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def upload_clip(self, video_id: str, file_path: str, clip_index: int) -> str:
        clips_dir = self._clips_dir(video_id)
        clips_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(file_path).suffix or ".mp4"
        dest = clips_dir / f"clip_{clip_index:03d}{ext}"
        shutil.copy2(file_path, dest)
        return str(dest)

    def upload_reel(self, video_id: str, file_path: str) -> str:
        clips_dir = self._clips_dir(video_id)
        clips_dir.mkdir(parents=True, exist_ok=True)
        dest = clips_dir / "reel.mp4"
        shutil.copy2(file_path, dest)
        return str(dest)

    def upload_manifest(self, video_id: str, manifest: dict) -> str:
        clips_dir = self._clips_dir(video_id)
        clips_dir.mkdir(parents=True, exist_ok=True)
        dest = clips_dir / "manifest.json"
        dest.write_text(json.dumps(manifest, indent=2))
        return str(dest)

    def download_video(self, video_id: str, destination: str) -> str:
        """Copy the original video to a destination directory."""
        video_dir = self._video_dir(video_id)
        originals = list(video_dir.glob("original.*"))
        if not originals:
            raise FileNotFoundError(f"Video not found for id: {video_id}")
        src = originals[0]
        dest = Path(destination) / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return str(dest)

    def get_video_path(self, video_id: str) -> Optional[str]:
        """Get the direct path to the original video file."""
        video_dir = self._video_dir(video_id)
        if not video_dir.exists():
            return None
        originals = list(video_dir.glob("original.*"))
        return str(originals[0]) if originals else None

    def get_reel_path(self, video_id: str) -> Optional[str]:
        """Get the direct path to the reel file."""
        reel = self._clips_dir(video_id) / "reel.mp4"
        return str(reel) if reel.exists() else None

    def video_exists(self, video_id: str) -> bool:
        video_dir = self._video_dir(video_id)
        return any(video_dir.glob("original.*")) if video_dir.exists() else False

    def list_clips(self, video_id: str) -> list[str]:
        clips_dir = self._clips_dir(video_id)
        if not clips_dir.exists():
            return []
        return sorted(str(p) for p in clips_dir.glob("clip_*"))

    def get_reel_url(self, video_id: str) -> Optional[str]:
        """Return a local API URL for the reel."""
        if self.get_reel_path(video_id):
            return f"/api/files/clips/{video_id}/reel.mp4"
        return None


_storage_service = None


def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
