"""
Examples:
poetry run python src/main.py --videos "video1.mp4,video2.mp4,video3.mp4" --csv "data.csv"


args:
--directory "/path/to/different/folder"
"""

import argparse
import os
import sys
import ipdb

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import pandas as pd
from moviepy.editor import VideoFileClip, concatenate_videoclips
from config import Config

# Load environment variables from .env file
load_dotenv()

# Get configuration
config = Config.from_env()
before_goal_seconds = config.before_goal_seconds
after_goal_seconds = config.after_goal_seconds

# Determine default directory for files
DEFAULT_DIR = os.getenv("FILE_DIR", os.path.dirname(os.path.abspath(__file__)))

import pdb


def parse_time_to_seconds(t):
    """
    Converts a time string in HH:MM:SS or MM:SS format to seconds.
    """
    parts = t.split(":")
    if len(parts) == 3:  # HH:MM:SS format
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    elif len(parts) == 2:  # MM:SS format
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    else:
        return float(parts[0])  # Handle case where the input is already in seconds


def main(video_files, directory, date, save_full_video=None, skip_highlights=False):
    print(DEFAULT_DIR)

    # Override config if save_full_video is explicitly set
    if save_full_video is not None:
        config.save_full_video = save_full_video
    # Build full paths to the CSV and video files
    base_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    date_folder = os.path.join(directory, date)

    # If video_files is None, auto-discover all MP4 files in the date folder
    if video_files is None:
        # Exclude output files from auto-discovery
        exclude_files = {config.output_filename.lower(), config.full_video_filename.lower()}
        mp4_files = sorted(
            [f for f in os.listdir(date_folder)
             if f.lower().endswith(".mp4") and f.lower() not in exclude_files]
        )
        if not mp4_files:
            print(f"No MP4 files found in {date_folder}")
            sys.exit(1)
        print(f"Found {len(mp4_files)} MP4 files: {', '.join(mp4_files)}")
        video_paths = [os.path.join(date_folder, f) for f in mp4_files]
    else:
        video_paths = [
            os.path.join(date_folder, v.strip()) for v in video_files.split(",")
        ]

    # Step 1: Read CSV (skip if only creating full video)
    if not skip_highlights:
        csv_path = os.path.join(date_folder, "splits.csv")
        df = pd.read_csv(csv_path)
        cumulative_times = df["Cumulative Time"].apply(parse_time_to_seconds).tolist()
    else:
        cumulative_times = []

    # Step 2: Load and concatenate video files
    clips = [VideoFileClip(v) for v in video_paths]
    # import pdb

    # pdb.set_trace()

    full_clip = concatenate_videoclips(clips)

    # Save the full uncut video if enabled
    if config.save_full_video:
        full_video_path = config.get_full_video_path(date)
        print(f"Saving full uncut video to: {full_video_path}")
        print(f"This may take several minutes for large videos...")
        try:
            full_clip.write_videofile(
                full_video_path,
                codec=config.video_codec,
                audio_codec=config.audio_codec,
                threads=4,  # Use multiple threads for faster encoding
                preset='faster'  # Use faster encoding preset
            )
            print(f"Full uncut video saved to: {full_video_path}")
        except Exception as e:
            print(f"Error saving full video: {e}")
            print("Continuing with highlight creation...")

    # ipdb.set_trace()
    # Step 3: Create and concatenate subclips based on cumulative times (skip if --skip-highlights)
    if not skip_highlights:
        final_clips = []
        print(len(cumulative_times))
        print(f"Full clip duration: {full_clip.duration} seconds")

        for t in cumulative_times:
            # Skip timestamps that exceed video duration
            if t > full_clip.duration:
                print(
                    f"Skipping timestamp {t} as it exceeds video duration ({full_clip.duration})"
                )
                continue

            start = max(t - before_goal_seconds, 0)
            end = min(t + after_goal_seconds, full_clip.duration)
            print(f"Creating subclip from {start} to {end} based on t={t}")
            subclip = full_clip.subclip(start, end)
            final_clips.append(subclip)

    # Step 4: Concatenate all the subclips into a final video
    if not skip_highlights and final_clips:
        final_video = concatenate_videoclips(final_clips)
        output_path = config.get_output_path(date)

        try:
            final_video.write_videofile(
                output_path,
                codec=config.video_codec,
                audio_codec=config.audio_codec,
                threads=4,
                preset='faster',
                logger='bar'  # Force progress bar output
            )

            # Verify the file was actually created and has content
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"Highlights video saved to: {output_path}")
                print(f"File size: {file_size / (1024*1024):.2f} MB")
            else:
                print(f"ERROR: File was not created at {output_path}")
                sys.exit(1)
        except Exception as e:
            print(f"Error saving highlights video: {e}")
            raise
        finally:
            # Clean up
            final_video.close()
    elif not skip_highlights:
        print("No clips to produce from the given timestamps.")

    if skip_highlights:
        print("Skipped highlights creation (--skip-highlights flag was set)")

    # Clean up video clips to free memory
    full_clip.close()
    for clip in clips:
        clip.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process videos and timestamps from a CSV."
    )
    parser.add_argument(
        "--videos",
        type=str,
        required=False,
        default=None,
        help="Comma-separated video file names (optional - will auto-discover MP4s if not provided)",
    )
    parser.add_argument(
        "--directory",
        type=str,
        default=DEFAULT_DIR,
        help="Directory where the CSV and videos are located",
    )
    parser.add_argument(
        "--date", type=str, required=True, help="Date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--save-full-video",
        dest="save_full_video",
        action="store_true",
        default=None,
        help="Save the full uncut video alongside highlights"
    )
    parser.add_argument(
        "--no-save-full-video",
        dest="save_full_video",
        action="store_false",
        default=None,
        help="Don't save the full uncut video"
    )
    parser.add_argument(
        "--skip-highlights",
        dest="skip_highlights",
        action="store_true",
        default=False,
        help="Skip highlights creation and only produce the full video"
    )
    args = parser.parse_args()
    main(args.videos, args.directory, args.date, args.save_full_video, args.skip_highlights)
