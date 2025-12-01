"""Command-line interface for YouTube uploads."""

import argparse
import sys

from .auth import authenticate_only
from .uploader import upload_video, YouTubeUploadError


def main():
    parser = argparse.ArgumentParser(
        description="Upload videos to YouTube",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # First-time authentication setup
  poetry run python -m src.youtube.cli --auth-only

  # Upload a video
  poetry run python -m src.youtube.cli \\
      --file "path/to/video.mp4" \\
      --title "Indoor Football Highlights - 2025-01-15"

  # Upload with all options
  poetry run python -m src.youtube.cli \\
      --file "path/to/video.mp4" \\
      --title "Game Highlights" \\
      --description "Great game!" \\
      --tags "indoor football,highlights,goals" \\
      --privacy unlisted
        """,
    )

    # Authentication only mode
    parser.add_argument(
        "--auth-only",
        action="store_true",
        help="Only run authentication (first-time setup)",
    )

    # Required for upload (unless --auth-only)
    parser.add_argument(
        "--file",
        type=str,
        help="Path to video file to upload",
    )
    parser.add_argument(
        "--title",
        type=str,
        help="Video title",
    )

    # Optional metadata
    parser.add_argument(
        "--description",
        type=str,
        default="",
        help="Video description",
    )
    parser.add_argument(
        "--tags",
        type=str,
        default="indoor football,highlights",
        help="Comma-separated tags (default: 'indoor football,highlights')",
    )
    parser.add_argument(
        "--category",
        type=str,
        default="17",
        help="YouTube category ID (default: 17 = Sports)",
    )
    parser.add_argument(
        "--privacy",
        type=str,
        choices=["public", "private", "unlisted"],
        default="unlisted",
        help="Privacy status (default: unlisted)",
    )

    args = parser.parse_args()

    # Handle auth-only mode
    if args.auth_only:
        print("Running authentication setup...")
        success = authenticate_only()
        sys.exit(0 if success else 1)

    # Validate required arguments for upload
    if not args.file:
        parser.error("--file is required for upload (or use --auth-only)")
    if not args.title:
        parser.error("--title is required for upload")

    # Parse tags
    tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]

    # Upload
    try:
        result = upload_video(
            video_path=args.file,
            title=args.title,
            description=args.description,
            tags=tags,
            category_id=args.category,
            privacy_status=args.privacy,
        )
        print(f"\nSuccess! Video ID: {result['video_id']}")
        print(f"URL: {result['url']}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except YouTubeUploadError as e:
        print(f"Upload error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
