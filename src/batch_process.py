"""Batch process multiple date folders and optionally upload to YouTube."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from config import Config

load_dotenv()

config = Config.from_env()

# State file for tracking uploads
STATE_FILE = Path(__file__).parent.parent / "upload_state.json"

# QUOTA PROTECTION
# YouTube API: 10,000 units/day, each upload costs ~1,600 units
# Safe limit: 6 uploads per day (but we'll cap lower to be safe)
MAX_UPLOADS_PER_RUN = 4  # Max videos to upload in a single run (2 dates worth)
UPLOAD_WARNING_THRESHOLD = 6  # Warn when approaching daily limit


def load_upload_state() -> dict:
    """Load upload state from JSON file."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"_meta": {"uploads_today": 0, "last_upload_date": None}}


def get_uploads_today(state: dict) -> int:
    """Get count of uploads done today."""
    meta = state.get("_meta", {})
    last_date = meta.get("last_upload_date")
    today = datetime.now().strftime("%Y-%m-%d")

    if last_date != today:
        # Reset counter for new day
        return 0
    return meta.get("uploads_today", 0)


def increment_upload_count(state: dict) -> None:
    """Increment today's upload counter."""
    today = datetime.now().strftime("%Y-%m-%d")

    if "_meta" not in state:
        state["_meta"] = {}

    if state["_meta"].get("last_upload_date") != today:
        state["_meta"]["uploads_today"] = 1
        state["_meta"]["last_upload_date"] = today
    else:
        state["_meta"]["uploads_today"] = state["_meta"].get("uploads_today", 0) + 1

    save_upload_state(state)


def save_upload_state(state: dict) -> None:
    """Save upload state to JSON file."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def is_video_uploaded(state: dict, date: str, video_type: str) -> bool:
    """Check if a video has already been uploaded."""
    return date in state and video_type in state[date]


def record_upload(state: dict, date: str, video_type: str, video_id: str) -> None:
    """Record a successful upload in state."""
    if date not in state:
        state[date] = {}
    state[date][video_type] = {
        "youtube_id": video_id,
        "uploaded_at": datetime.now().isoformat(),
    }
    save_upload_state(state)


def check_folder_status(date: str) -> dict:
    """Check what exists in a date folder."""
    date_folder = os.path.join(config.base_directory, date)

    status = {
        "exists": os.path.isdir(date_folder),
        "has_splits_csv": False,
        "has_full_video": False,
        "has_highlights": False,
        "mp4_count": 0,
    }

    if not status["exists"]:
        return status

    status["has_splits_csv"] = os.path.exists(os.path.join(date_folder, "splits.csv"))
    status["has_full_video"] = os.path.exists(
        os.path.join(date_folder, config.full_video_filename)
    )
    status["has_highlights"] = os.path.exists(
        os.path.join(date_folder, config.output_filename)
    )

    # Count source MP4 files (exclude output files)
    exclude_files = {config.output_filename.lower(), config.full_video_filename.lower()}
    mp4_files = [
        f
        for f in os.listdir(date_folder)
        if f.lower().endswith(".mp4") and f.lower() not in exclude_files
    ]
    status["mp4_count"] = len(mp4_files)

    return status


def process_folder(date: str, force: bool = False) -> dict:
    """
    Process a single date folder.

    Returns dict with results for full_video and highlights.
    """
    status = check_folder_status(date)
    result = {
        "date": date,
        "full_video": {"action": "skipped", "path": None},
        "highlights": {"action": "skipped", "path": None},
    }

    if not status["exists"]:
        print(f"  Folder not found: {date}")
        result["full_video"]["action"] = "error"
        result["highlights"]["action"] = "error"
        return result

    if status["mp4_count"] == 0:
        print(f"  No source MP4 files found in {date}")
        result["full_video"]["action"] = "error"
        result["highlights"]["action"] = "error"
        return result

    date_folder = os.path.join(config.base_directory, date)
    full_video_path = os.path.join(date_folder, config.full_video_filename)
    highlights_path = os.path.join(date_folder, config.output_filename)

    # Determine what needs to be done
    need_full_video = force or not status["has_full_video"]
    need_highlights = (force or not status["has_highlights"]) and status[
        "has_splits_csv"
    ]

    if not need_full_video and not need_highlights:
        print(f"  Both videos already exist, skipping")
        result["full_video"]["path"] = full_video_path
        result["highlights"]["path"] = highlights_path
        return result

    # Build command
    cmd = [
        "poetry",
        "run",
        "python",
        "src/main.py",
        "--date",
        date,
        "--directory",
        config.base_directory,
    ]

    if need_full_video:
        cmd.append("--save-full-video")
    else:
        cmd.append("--no-save-full-video")

    if not need_highlights or not status["has_splits_csv"]:
        cmd.append("--skip-highlights")
        if not status["has_splits_csv"]:
            print(f"  Warning: No splits.csv found, skipping highlights")

    print(f"  Running: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True, cwd=Path(__file__).parent.parent)

        if need_full_video and os.path.exists(full_video_path):
            result["full_video"]["action"] = "created"
            result["full_video"]["path"] = full_video_path
        elif status["has_full_video"]:
            result["full_video"]["path"] = full_video_path

        if need_highlights and os.path.exists(highlights_path):
            result["highlights"]["action"] = "created"
            result["highlights"]["path"] = highlights_path
        elif status["has_highlights"]:
            result["highlights"]["path"] = highlights_path

    except subprocess.CalledProcessError as e:
        print(f"  Error processing {date}: {e}")
        result["full_video"]["action"] = "error"
        result["highlights"]["action"] = "error"

    return result


def upload_videos(
    date: str, state: dict, privacy: str = "unlisted", uploads_this_run: int = 0,
    max_uploads: int = MAX_UPLOADS_PER_RUN
) -> tuple[dict, int]:
    """
    Upload videos for a date folder to YouTube.

    Returns (results dict, updated uploads_this_run count)
    """
    from src.youtube import upload_video

    date_folder = os.path.join(config.base_directory, date)
    results = {"full_video": None, "highlights": None}

    uploads_today = get_uploads_today(state)

    # Check quota limits
    if uploads_this_run >= max_uploads:
        print(f"  QUOTA PROTECTION: Reached max uploads per run ({max_uploads})")
        print(f"  Run again to continue uploading more videos")
        return results, uploads_this_run

    if uploads_today >= UPLOAD_WARNING_THRESHOLD:
        print(f"  WARNING: Approaching daily quota limit ({uploads_today} uploads today)")
        print(f"  YouTube allows ~6 uploads/day. Quota resets at midnight Pacific Time.")

    # Upload full video
    full_video_path = os.path.join(date_folder, config.full_video_filename)
    if os.path.exists(full_video_path):
        if is_video_uploaded(state, date, "full_video"):
            print(f"  Full video already uploaded, skipping")
        elif uploads_this_run >= max_uploads:
            print(f"  Full video skipped (quota protection)")
        else:
            print(f"  Uploading full video... (upload {uploads_this_run + 1}/{max_uploads} this run)")
            try:
                result = upload_video(
                    video_path=full_video_path,
                    title=f"{date} - Full Match",
                    description=f"Indoor football full match from {date}",
                    tags=["indoor football", "full match", date],
                    privacy_status=privacy,
                )
                record_upload(state, date, "full_video", result["video_id"])
                increment_upload_count(state)
                uploads_this_run += 1
                results["full_video"] = result
                print(f"  Full video uploaded: {result['url']}")
            except Exception as e:
                print(f"  Error uploading full video: {e}")

    # Upload highlights
    highlights_path = os.path.join(date_folder, config.output_filename)
    if os.path.exists(highlights_path):
        if is_video_uploaded(state, date, "highlights"):
            print(f"  Highlights already uploaded, skipping")
        elif uploads_this_run >= max_uploads:
            print(f"  Highlights skipped (quota protection)")
        else:
            print(f"  Uploading highlights... (upload {uploads_this_run + 1}/{max_uploads} this run)")
            try:
                result = upload_video(
                    video_path=highlights_path,
                    title=f"{date} - Highlights",
                    description=f"Indoor football highlights from {date}",
                    tags=["indoor football", "highlights", "goals", date],
                    privacy_status=privacy,
                )
                record_upload(state, date, "highlights", result["video_id"])
                increment_upload_count(state)
                uploads_this_run += 1
                results["highlights"] = result
                print(f"  Highlights uploaded: {result['url']}")
            except Exception as e:
                print(f"  Error uploading highlights: {e}")

    return results, uploads_this_run


def main():
    parser = argparse.ArgumentParser(
        description="Batch process date folders and upload to YouTube",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process specific folders
  poetry run python src/batch_process.py --dates "2025-01-13,2025-01-20,2025-01-27"

  # Process and upload
  poetry run python src/batch_process.py --dates "2025-01-13,2025-01-20" --upload

  # Dry run (show what would be done)
  poetry run python src/batch_process.py --dates "2025-01-13,2025-01-20" --dry-run

  # Force reprocess
  poetry run python src/batch_process.py --dates "2025-01-13" --force

  # Upload only (skip processing, just upload existing videos)
  poetry run python src/batch_process.py --dates "2025-01-13" --upload-only
        """,
    )

    parser.add_argument(
        "--dates",
        type=str,
        required=True,
        help="Comma-separated list of date folders (e.g., '2025-01-13,2025-01-20')",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload videos to YouTube after processing",
    )
    parser.add_argument(
        "--upload-only",
        action="store_true",
        help="Skip processing, only upload existing videos",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reprocess even if videos already exist",
    )
    parser.add_argument(
        "--privacy",
        type=str,
        choices=["public", "private", "unlisted"],
        default="unlisted",
        help="YouTube privacy status (default: unlisted)",
    )
    parser.add_argument(
        "--max-uploads",
        type=int,
        default=MAX_UPLOADS_PER_RUN,
        help=f"Max videos to upload this run (default: {MAX_UPLOADS_PER_RUN}, max safe: 6/day)",
    )

    args = parser.parse_args()

    # Override max uploads if specified
    max_uploads = args.max_uploads

    # Parse dates
    dates = [d.strip() for d in args.dates.split(",") if d.strip()]
    if not dates:
        print("Error: No dates provided")
        sys.exit(1)

    print(f"Processing {len(dates)} date folders")
    print(f"Base directory: {config.base_directory}")
    print()

    # Dry run - just show status
    if args.dry_run:
        print("=== DRY RUN ===\n")
        for date in dates:
            status = check_folder_status(date)
            print(f"{date}:")
            print(f"  Folder exists: {status['exists']}")
            if status["exists"]:
                print(f"  Source MP4s: {status['mp4_count']}")
                print(f"  Has splits.csv: {status['has_splits_csv']}")
                print(f"  Has full_video.mp4: {status['has_full_video']}")
                print(f"  Has final_video.mp4: {status['has_highlights']}")

                would_process_full = not status["has_full_video"] or args.force
                would_process_highlights = (
                    not status["has_highlights"] or args.force
                ) and status["has_splits_csv"]
                print(f"  Would create full video: {would_process_full}")
                print(f"  Would create highlights: {would_process_highlights}")
            print()
        return

    # Load upload state
    upload_state = load_upload_state()
    uploads_this_run = 0

    # Show quota status
    uploads_today = get_uploads_today(upload_state)
    if uploads_today > 0:
        print(f"Uploads today so far: {uploads_today}")
    print(f"Max uploads this run: {max_uploads}")
    print()

    # Process folders
    results = []
    for i, date in enumerate(dates, 1):
        print(f"\n[{i}/{len(dates)}] Processing {date}:")

        if not args.upload_only:
            result = process_folder(date, force=args.force)
            results.append(result)

        if args.upload or args.upload_only:
            _, uploads_this_run = upload_videos(
                date, upload_state, privacy=args.privacy, uploads_this_run=uploads_this_run,
                max_uploads=max_uploads
            )
            if uploads_this_run >= max_uploads:
                print(f"\n*** STOPPING: Reached upload limit ({max_uploads}) for this run ***")
                print(f"*** Run again to continue with remaining dates ***")
                break

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    if not args.upload_only:
        created_full = sum(1 for r in results if r["full_video"]["action"] == "created")
        created_highlights = sum(
            1 for r in results if r["highlights"]["action"] == "created"
        )
        errors = sum(
            1
            for r in results
            if r["full_video"]["action"] == "error"
            or r["highlights"]["action"] == "error"
        )

        print(f"Full videos created: {created_full}")
        print(f"Highlights created: {created_highlights}")
        print(f"Errors: {errors}")

    if args.upload or args.upload_only:
        print(f"\nUpload state saved to: {STATE_FILE}")


if __name__ == "__main__":
    main()
