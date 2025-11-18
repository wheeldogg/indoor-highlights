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


from dotenv import load_dotenv
import pandas as pd
from moviepy.editor import VideoFileClip, concatenate_videoclips

# Load environment variables from .env file
load_dotenv()

before_goal_seconds = 8
after_goal_seconds = 4

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


def main(video_files, directory, date):
    print(DEFAULT_DIR)
    # Build full paths to the CSV and video files
    base_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    date_folder = os.path.join(directory, date)

    # If video_files is None, auto-discover all MP4 files in the date folder
    if video_files is None:
        mp4_files = sorted(
            [f for f in os.listdir(date_folder) if f.lower().endswith(".mp4")]
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

    # CSV is always splits.csv in the date folder
    csv_path = os.path.join(date_folder, "splits.csv")

    # Step 1: Read CSV
    df = pd.read_csv(csv_path)
    cumulative_times = df["Cumulative Time"].apply(parse_time_to_seconds).tolist()

    # Step 2: Load and concatenate video files

    clips = [VideoFileClip(v) for v in video_paths]
    # import pdb

    # pdb.set_trace()

    full_clip = concatenate_videoclips(clips)

    # ipdb.set_trace()
    # Step 3: Create and concatenate subclips based on cumulative times
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
    if final_clips:
        final_video = concatenate_videoclips(final_clips)
        output_path = os.path.join(date_folder, "final_video.mp4")
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
        print(f"Final video saved to: {output_path}")
    else:
        print("No clips to produce from the given timestamps.")


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
    args = parser.parse_args()
    main(args.videos, args.directory, args.date)
