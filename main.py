import pandas as pd
from moviepy.editor import VideoFileClip, concatenate_videoclips


def parse_time_to_seconds(t):
    """
    Given a time value from the CSV, convert it to seconds.
    This might be unnecessary if the CSV already has numeric values in seconds.
    If the CSV column is already numeric (seconds), just return t as is.
    If it's a string like 'HH:MM:SS', parse it accordingly.
    """
    # Example assuming it's just a number of seconds in a float or int form:
    return float(t)


def main():
    # Step 1: Read CSV
    df = pd.read_csv("data.csv")

    # We assume "Cumulative Time" is a column in the CSV:
    # If the CSV headers are "Laps", "Time", "Cumulative Time", ...
    # make sure to reference it exactly as in the CSV.
    cumulative_times = df["Cumulative Time"].apply(parse_time_to_seconds).tolist()

    # Step 2: Concatenate three MP4 files into one single video:
    # Load each video file
    clip1 = VideoFileClip("video1.mp4")
    clip2 = VideoFileClip("video2.mp4")
    clip3 = VideoFileClip("video3.mp4")

    # Concatenate all into one big clip
    full_clip = concatenate_videoclips([clip1, clip2, clip3])

    # Step 3: Create subclips around each cumulative time
    # For each cumulative time t, we want a segment [t-30, t+30].
    # We must ensure these times are within the video duration.
    final_clips = []
    for t in cumulative_times:
        start = max(t - 30, 0)  # don't go before the start of the video
        end = min(t + 30, full_clip.duration)  # don't go beyond the end
        subclip = full_clip.subclip(start, end)
        final_clips.append(subclip)

    # Step 4: Concatenate all the subclips into a final video
    if final_clips:
        final_video = concatenate_videoclips(final_clips)
        # Step 5: Write the final video to disk
        final_video.write_videofile(
            "final_video.mp4", codec="libx264", audio_codec="aac"
        )
    else:
        print("No clips to produce from the given timestamps.")


if __name__ == "__main__":
    main()
