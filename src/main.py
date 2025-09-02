"""
Indoor highlights video processor.

Examples:
poetry run python src/main.py --videos "video1.mp4,video2.mp4,video3.mp4" --csv "data.csv" --date 2025-07-28
poetry run python src/main.py --videos "MAH02309.mp4,MAH02310.mp4,MAH02311.mp4" --csv "/Users/swhelan/Dropbox/Indoor football/2025-07-28/splits.csv" --date 2025-07-28 --auto-move
"""

import argparse
import os
import sys
import shutil
from pathlib import Path

import pandas as pd
from moviepy.editor import VideoFileClip, concatenate_videoclips

# Import our config system
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config


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


def main(video_files, csv_file, date, auto_move=False, config=None):
    """Main processing function."""
    if config is None:
        config = Config.from_env()
    
    print(f"Processing videos for date: {date}")
    
    # Build full paths to the CSV and video files
    csv_path = config.get_csv_path(csv_file)
    video_paths = [
        config.get_video_path(date, v.strip()) for v in video_files.split(",")
    ]
    
    print(f"CSV file: {csv_path}")
    print(f"Video files: {video_paths}")

    # Step 1: Read CSV
    df = pd.read_csv(csv_path)
    cumulative_times = df["Cumulative Time"].apply(parse_time_to_seconds).tolist()

    # Step 2: Load and concatenate video files
    clips = [VideoFileClip(v) for v in video_paths]
    full_clip = concatenate_videoclips(clips)

    # Step 3: Create and concatenate subclips based on cumulative times
    final_clips = []
    print(f"Found {len(cumulative_times)} timestamps")
    print(f"Full clip duration: {full_clip.duration} seconds")

    for t in cumulative_times:
        # Skip timestamps that exceed video duration
        if t > full_clip.duration:
            print(
                f"Skipping timestamp {t} as it exceeds video duration ({full_clip.duration})"
            )
            continue

        start = max(t - config.before_goal_seconds, 0)
        end = min(t + config.after_goal_seconds, full_clip.duration)
        print(f"Creating subclip from {start} to {end} based on t={t}")
        subclip = full_clip.subclip(start, end)
        final_clips.append(subclip)

    # Step 4: Concatenate all the subclips into a final video
    if final_clips:
        output_file = config.output_filename
        final_video = concatenate_videoclips(final_clips)
        final_video.write_videofile(
            output_file, codec=config.video_codec, audio_codec=config.audio_codec
        )
        
        # Step 5: Auto-move the output file if requested
        if auto_move:
            destination = config.get_output_path(date)
            destination_dir = os.path.dirname(destination)
            
            # Create destination directory if it doesn't exist
            Path(destination_dir).mkdir(parents=True, exist_ok=True)
            
            print(f"Moving {output_file} to {destination}")
            shutil.move(output_file, destination)
            print(f"Video saved to: {destination}")
        else:
            print(f"Video saved as: {output_file}")
            print(f"To move to destination, run: mv {output_file} \"{config.get_output_path(date)}\"")
    else:
        print("No clips to produce from the given timestamps.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process videos and timestamps from a CSV to create highlight reel."
    )
    parser.add_argument(
        "--videos", type=str, required=True, help="Comma-separated video file names"
    )
    parser.add_argument("--csv", type=str, required=True, help="CSV file path")
    parser.add_argument(
        "--date", type=str, required=True, help="Date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--auto-move", action="store_true", 
        help="Automatically move output file to the date directory"
    )
    args = parser.parse_args()
    main(args.videos, args.csv, args.date, args.auto_move)
