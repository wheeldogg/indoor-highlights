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
from moviepy import VideoFileClip, concatenate_videoclips

# Load environment variables from .env file
load_dotenv()

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


def main(video_files, csv_file, directory, date):
    print(DEFAULT_DIR)
    # Build full paths to the CSV and video files
    base_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_directory = os.path.join(base_directory, "data")
    csv_path = os.path.join(csv_directory, csv_file)
    video_paths = [
        os.path.join(directory, date, v.strip()) for v in video_files.split(",")
    ]

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
    cumulative_times = cumulative_times[0:5]

    print(len(cumulative_times))

    for t in cumulative_times:
        start = max(t - 30, 0)
        end = min(t + 30, full_clip.duration)
        subclip = full_clip.subclipped(start, end)
        final_clips.append(subclip)

    # Step 4: Concatenate all the subclips into a final video
    if final_clips:
        final_video = concatenate_videoclips(final_clips)
        final_video.write_videofile(
            "final_video.mp4", codec="libx264", audio_codec="aac"
        )
    else:
        print("No clips to produce from the given timestamps.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process videos and timestamps from a CSV."
    )
    parser.add_argument(
        "--videos", type=str, required=True, help="Comma-separated video file names"
    )
    parser.add_argument("--csv", type=str, required=True, help="CSV file name")
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
    main(args.videos, args.csv, args.directory, args.date)
