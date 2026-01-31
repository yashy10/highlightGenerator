"""Configuration management using Pydantic Settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_cloud_project: str = ""
    gcs_bucket: str = "scorevision-videos"
    gemini_api_key: str = ""
    cors_origins: str = "*"
    max_video_size_mb: int = 500
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
