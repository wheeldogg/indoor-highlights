"""Process all folders: backup existing highlights and generate full videos."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from config import Config

load_dotenv()
config = Config.from_env()


def check_files_accessible(date_folder: str) -> tuple[bool, str]:
    """Check if files in folder are accessible (not cloud-only placeholders)."""
    folder_path = os.path.join(config.base_directory, date_folder)

    if not os.path.isdir(folder_path):
        return False, "Folder does not exist"

    # Find MP4 files (exclude output files)
    exclude = {config.output_filename.lower(), config.full_video_filename.lower()}
    mp4_files = [
        f for f in os.listdir(folder_path)
        if f.lower().endswith(".mp4") and f.lower() not in exclude
    ]

    if not mp4_files:
        return False, "No source MP4 files found"

    # Check if first MP4 has content (not 0 bytes)
    first_mp4 = os.path.join(folder_path, mp4_files[0])
    size = os.path.getsize(first_mp4)

    if size == 0:
        return False, f"Files are cloud-only (0 bytes). Make '{date_folder}' available offline in Dropbox first."

    return True, f"OK - {len(mp4_files)} MP4 files, first file is {size / (1024*1024):.1f} MB"


def backup_final_video(date_folder: str) -> bool:
    """Backup existing final_video.mp4 to final_video_original.mp4."""
    folder_path = os.path.join(config.base_directory, date_folder)
    final_video = os.path.join(folder_path, config.output_filename)
    backup_path = os.path.join(folder_path, "final_video_original.mp4")

    if not os.path.exists(final_video):
        print(f"  No existing {config.output_filename} to backup")
        return False

    if os.path.exists(backup_path):
        print(f"  Backup already exists: final_video_original.mp4")
        return True

    # Check if source has content
    if os.path.getsize(final_video) == 0:
        print(f"  {config.output_filename} is 0 bytes (cloud-only), skipping backup")
        return False

    print(f"  Backing up {config.output_filename} -> final_video_original.mp4")
    shutil.copy2(final_video, backup_path)
    return True


def process_folder(date_folder: str, dry_run: bool = False) -> bool:
    """Process a single folder: backup highlights, generate full video and new highlights."""
    print(f"\nProcessing {date_folder}:")

    # Check accessibility
    accessible, msg = check_files_accessible(date_folder)
    print(f"  Status: {msg}")

    if not accessible:
        return False

    if dry_run:
        folder_path = os.path.join(config.base_directory, date_folder)
        has_final = os.path.exists(os.path.join(folder_path, config.output_filename))
        has_full = os.path.exists(os.path.join(folder_path, config.full_video_filename))
        has_splits = os.path.exists(os.path.join(folder_path, "splits.csv"))

        print(f"  Has final_video.mp4: {has_final}")
        print(f"  Has full_video.mp4: {has_full}")
        print(f"  Has splits.csv: {has_splits}")
        print(f"  Would backup final_video: {has_final}")
        print(f"  Would create full_video: True")
        print(f"  Would create new final_video: {has_splits}")
        return True

    # Backup existing final_video.mp4
    backup_final_video(date_folder)

    # Run processing
    cmd = [
        "poetry", "run", "python", "src/main.py",
        "--date", date_folder,
        "--directory", config.base_directory,
        "--save-full-video",  # Always create full video
    ]

    # Check if splits.csv exists for highlights
    folder_path = os.path.join(config.base_directory, date_folder)
    if not os.path.exists(os.path.join(folder_path, "splits.csv")):
        cmd.append("--skip-highlights")
        print(f"  No splits.csv, will only create full video")

    print(f"  Running: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True, cwd=Path(__file__).parent.parent)
        print(f"  Done!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Process folders: backup highlights and generate full videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test on one folder first
  poetry run python src/process_all.py --test 2025-10-13

  # Dry run to see what would happen
  poetry run python src/process_all.py --dry-run

  # Process all (excluding 2025-11-10 and 2025-11-17)
  poetry run python src/process_all.py

  # Process specific folders
  poetry run python src/process_all.py --dates "2025-01-13,2025-02-24"
        """
    )

    parser.add_argument(
        "--test",
        type=str,
        help="Test on a single folder first",
    )
    parser.add_argument(
        "--dates",
        type=str,
        help="Comma-separated list of specific dates to process",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without doing it",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default="2025-11-10,2025-11-17",
        help="Comma-separated list of dates to exclude (default: 2025-11-10,2025-11-17)",
    )

    args = parser.parse_args()

    # Determine which folders to process
    if args.test:
        folders = [args.test]
        print(f"TEST MODE: Processing only {args.test}")
    elif args.dates:
        folders = [d.strip() for d in args.dates.split(",") if d.strip()]
    else:
        # Get all date folders
        exclude = set(d.strip() for d in args.exclude.split(",") if d.strip())
        all_folders = sorted([
            f for f in os.listdir(config.base_directory)
            if os.path.isdir(os.path.join(config.base_directory, f))
            and f.startswith("202")
            and f not in exclude
        ])
        folders = all_folders
        print(f"Processing {len(folders)} folders (excluding: {', '.join(exclude)})")

    if args.dry_run:
        print("\n=== DRY RUN ===")

    # Process each folder
    success = 0
    failed = 0
    skipped = 0

    for folder in folders:
        result = process_folder(folder, dry_run=args.dry_run)
        if result:
            success += 1
        else:
            # Check if it was just inaccessible
            accessible, _ = check_files_accessible(folder)
            if not accessible:
                skipped += 1
            else:
                failed += 1

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Success: {success}")
    print(f"Failed: {failed}")
    print(f"Skipped (inaccessible): {skipped}")

    if skipped > 0:
        print("\nTo fix skipped folders:")
        print("1. Open Dropbox")
        print("2. Right-click each folder -> 'Make Available Offline'")
        print("3. Run this script again")


if __name__ == "__main__":
    main()
