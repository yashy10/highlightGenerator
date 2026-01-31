"""Google Cloud Storage service for video and clip management."""
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, BinaryIO

from google.cloud import storage
from google.cloud.exceptions import NotFound

from config import get_settings


class StorageService:
    def __init__(self):
        self.settings = get_settings()
        self.client = storage.Client(project=self.settings.google_cloud_project or None)
        self.bucket = self.client.bucket(self.settings.gcs_bucket)
    
    def generate_video_id(self) -> str:
        return uuid.uuid4().hex[:12]
    
    def _get_blob_path(self, video_id: str, filename: str) -> str:
        return f"uploads/{video_id}/{filename}"
    
    def _get_clip_path(self, video_id: str, filename: str) -> str:
        return f"clips/{video_id}/{filename}"
    
    def upload_video(
        self,
        video_id: str,
        file: BinaryIO,
        content_type: str = "video/mp4",
        original_filename: str = "original.mp4",
    ) -> str:
        ext = Path(original_filename).suffix or ".mp4"
        blob_path = self._get_blob_path(video_id, f"original{ext}")
        blob = self.bucket.blob(blob_path)
        
        blob.upload_from_file(file, content_type=content_type)
        
        return f"gs://{self.settings.gcs_bucket}/{blob_path}"
    
    def upload_analysis(self, video_id: str, analysis: dict) -> str:
        blob_path = self._get_blob_path(video_id, "analysis.json")
        blob = self.bucket.blob(blob_path)
        
        blob.upload_from_string(
            json.dumps(analysis, indent=2),
            content_type="application/json",
        )
        
        return f"gs://{self.settings.gcs_bucket}/{blob_path}"
    
    def get_analysis(self, video_id: str) -> Optional[dict]:
        blob_path = self._get_blob_path(video_id, "analysis.json")
        blob = self.bucket.blob(blob_path)
        
        try:
            content = blob.download_as_text()
            return json.loads(content)
        except NotFound:
            return None
    
    def upload_clip(
        self,
        video_id: str,
        file_path: str,
        clip_index: int,
    ) -> str:
        ext = Path(file_path).suffix or ".mp4"
        blob_path = self._get_clip_path(video_id, f"clip_{clip_index:03d}{ext}")
        blob = self.bucket.blob(blob_path)
        
        blob.upload_from_filename(file_path, content_type="video/mp4")
        
        return f"gs://{self.settings.gcs_bucket}/{blob_path}"
    
    def upload_reel(self, video_id: str, file_path: str) -> str:
        blob_path = self._get_clip_path(video_id, "reel.mp4")
        blob = self.bucket.blob(blob_path)
        
        blob.upload_from_filename(file_path, content_type="video/mp4")
        
        return f"gs://{self.settings.gcs_bucket}/{blob_path}"
    
    def upload_manifest(self, video_id: str, manifest: dict) -> str:
        blob_path = self._get_clip_path(video_id, "manifest.json")
        blob = self.bucket.blob(blob_path)
        
        blob.upload_from_string(
            json.dumps(manifest, indent=2),
            content_type="application/json",
        )
        
        return f"gs://{self.settings.gcs_bucket}/{blob_path}"
    
    def download_video(self, video_id: str, destination: str) -> str:
        prefix = f"uploads/{video_id}/original"
        blobs = list(self.client.list_blobs(self.bucket, prefix=prefix))
        
        if not blobs:
            raise FileNotFoundError(f"Video not found for id: {video_id}")
        
        blob = blobs[0]
        ext = Path(blob.name).suffix or ".mp4"
        dest_path = Path(destination) / f"original{ext}"
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        blob.download_to_filename(str(dest_path))
        
        return str(dest_path)
    
    def get_signed_url(
        self,
        gcs_url: str,
        expiration_hours: int = 24,
    ) -> str:
        if gcs_url.startswith("gs://"):
            path = gcs_url.replace(f"gs://{self.settings.gcs_bucket}/", "")
        else:
            path = gcs_url
        
        blob = self.bucket.blob(path)
        
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=expiration_hours),
            method="GET",
        )
        
        return url
    
    def get_gcs_uri(self, video_id: str) -> Optional[str]:
        prefix = f"uploads/{video_id}/original"
        blobs = list(self.client.list_blobs(self.bucket, prefix=prefix))
        
        if not blobs:
            return None
        
        return f"gs://{self.settings.gcs_bucket}/{blobs[0].name}"
    
    def video_exists(self, video_id: str) -> bool:
        prefix = f"uploads/{video_id}/original"
        blobs = list(self.client.list_blobs(self.bucket, prefix=prefix, max_results=1))
        return len(blobs) > 0
    
    def list_clips(self, video_id: str) -> list[str]:
        prefix = f"clips/{video_id}/clip_"
        blobs = self.client.list_blobs(self.bucket, prefix=prefix)
        
        return [f"gs://{self.settings.gcs_bucket}/{blob.name}" for blob in blobs]
    
    def get_reel_url(self, video_id: str) -> Optional[str]:
        blob_path = self._get_clip_path(video_id, "reel.mp4")
        blob = self.bucket.blob(blob_path)
        
        if blob.exists():
            return f"gs://{self.settings.gcs_bucket}/{blob_path}"
        return None


storage_service = StorageService()


def get_storage_service() -> StorageService:
    return storage_service
