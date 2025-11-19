"""Configuration management for indoor highlights processing."""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Configuration for video processing."""
    
    # Timing settings
    before_goal_seconds: int = 8
    after_goal_seconds: int = 4
    
    # File paths
    base_directory: str = "/Users/swhelan/Dropbox/Indoor football"
    csv_directory: str = "data"
    output_filename: str = "final_video.mp4"
    full_video_filename: str = "full_video.mp4"

    # Video settings
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    save_full_video: bool = True  # Whether to save the full uncut video
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create config from environment variables."""
        return cls(
            before_goal_seconds=int(os.getenv("BEFORE_GOAL_SECONDS", 8)),
            after_goal_seconds=int(os.getenv("AFTER_GOAL_SECONDS", 4)),
            base_directory=os.getenv("BASE_DIRECTORY", "/Users/swhelan/Dropbox/Indoor football"),
            csv_directory=os.getenv("CSV_DIRECTORY", "data"),
            output_filename=os.getenv("OUTPUT_FILENAME", "final_video.mp4"),
            full_video_filename=os.getenv("FULL_VIDEO_FILENAME", "full_video.mp4"),
            video_codec=os.getenv("VIDEO_CODEC", "libx264"),
            audio_codec=os.getenv("AUDIO_CODEC", "aac"),
            save_full_video=os.getenv("SAVE_FULL_VIDEO", "true").lower() == "true",
        )
    
    def get_video_path(self, date: str, video_file: str) -> str:
        """Get full path to video file."""
        return os.path.join(self.base_directory, date, video_file)
    
    def get_csv_path(self, csv_file: str) -> str:
        """Get full path to CSV file."""
        return csv_file if os.path.isabs(csv_file) else os.path.join(self.csv_directory, csv_file)
    
    def get_output_path(self, date: Optional[str] = None) -> str:
        """Get output path for final video."""
        if date:
            return os.path.join(self.base_directory, date, self.output_filename)
        return self.output_filename

    def get_full_video_path(self, date: Optional[str] = None) -> str:
        """Get output path for full uncut video."""
        if date:
            return os.path.join(self.base_directory, date, self.full_video_filename)
        return self.full_video_filename