"""YouTube upload module for indoor-highlights."""

from .auth import get_authenticated_service
from .uploader import YouTubeUploader, upload_video

__all__ = ["get_authenticated_service", "YouTubeUploader", "upload_video"]
