"""YouTube video uploader with resumable upload support."""

import random
import time
from pathlib import Path

import httplib2
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from .auth import get_authenticated_service

# Retry configuration
MAX_RETRIES = 10
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError)

# YouTube category IDs
CATEGORY_SPORTS = "17"


class YouTubeUploadError(Exception):
    """Base exception for YouTube upload errors."""

    pass


class QuotaExceededError(YouTubeUploadError):
    """YouTube API quota exceeded."""

    pass


class UploadFailedError(YouTubeUploadError):
    """Video upload failed after retries."""

    pass


class YouTubeUploader:
    """Handles video uploads to YouTube with resumable upload support."""

    def __init__(self, youtube_service=None):
        """
        Initialize uploader.

        Args:
            youtube_service: Authenticated YouTube service (optional, will create if not provided)
        """
        self.youtube = youtube_service

    def _get_service(self):
        """Get or create YouTube service."""
        if self.youtube is None:
            self.youtube = get_authenticated_service()
        return self.youtube

    def upload(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: list[str] | None = None,
        category_id: str = CATEGORY_SPORTS,
        privacy_status: str = "unlisted",
        made_for_kids: bool = False,
    ) -> dict:
        """
        Upload video to YouTube.

        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            tags: List of tags
            category_id: YouTube category ID (17 = Sports)
            privacy_status: public, private, or unlisted
            made_for_kids: Whether video is made for kids

        Returns:
            dict with video_id and url on success

        Raises:
            YouTubeUploadError: On upload failure
        """
        video_file = Path(video_path)
        if not video_file.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        youtube = self._get_service()

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": made_for_kids,
            },
        }

        # Use resumable upload for large files
        media = MediaFileUpload(
            str(video_file),
            chunksize=1024 * 1024,  # 1MB chunks
            resumable=True,
            mimetype="video/*",
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        print(f"Uploading: {video_file.name}")
        response = self._resumable_upload(request)

        video_id = response["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        print(f"Upload complete! Video URL: {video_url}")

        return {
            "video_id": video_id,
            "url": video_url,
            "title": title,
        }

    def _resumable_upload(self, request) -> dict:
        """
        Execute upload with exponential backoff retry logic.

        Handles network interruptions and server errors.
        """
        response = None
        error = None
        retry = 0

        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"  Uploaded {progress}%")
            except HttpError as e:
                if e.resp.status == 403 and "quotaExceeded" in str(e):
                    raise QuotaExceededError(
                        "YouTube API quota exceeded. "
                        "Quota resets at midnight Pacific Time."
                    )
                if e.resp.status in RETRIABLE_STATUS_CODES:
                    error = f"Retriable HTTP error {e.resp.status}: {e.content}"
                else:
                    raise UploadFailedError(f"HTTP error {e.resp.status}: {e.content}")
            except RETRIABLE_EXCEPTIONS as e:
                error = f"Retriable error: {e}"

            if error:
                retry += 1
                if retry > MAX_RETRIES:
                    raise UploadFailedError(f"Max retries exceeded: {error}")

                sleep_seconds = random.random() * (2**retry)
                print(f"  Retry {retry}/{MAX_RETRIES} in {sleep_seconds:.1f}s...")
                time.sleep(sleep_seconds)
                error = None

        return response


def upload_video(
    video_path: str,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    category_id: str = CATEGORY_SPORTS,
    privacy_status: str = "unlisted",
    made_for_kids: bool = False,
    youtube_service=None,
) -> dict:
    """
    Convenience function to upload a video.

    Args:
        video_path: Path to video file
        title: Video title
        description: Video description
        tags: List of tags
        category_id: YouTube category ID (17 = Sports)
        privacy_status: public, private, or unlisted
        made_for_kids: Whether video is made for kids
        youtube_service: Optional authenticated YouTube service

    Returns:
        dict with video_id and url
    """
    uploader = YouTubeUploader(youtube_service)
    return uploader.upload(
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        category_id=category_id,
        privacy_status=privacy_status,
        made_for_kids=made_for_kids,
    )
