# Indoor Highlights

Create indoor football/soccer highlight reels from video files using Garmin timestamps. This tool processes multiple video files and creates both highlight clips and full uncut videos based on lap completion timestamps from your Garmin sports watch.

## Features

- Automatically concatenates multiple video files
- Extracts highlight moments based on Garmin CSV timestamps
- Creates clips with configurable padding (default: 8 seconds before, 4 seconds after each timestamp)
- **By default, saves both highlight clips AND full uncut video for YouTube uploads**
- Auto-discovers MP4 files in date folders
- Supports flexible timestamp formats (HH:MM:SS or MM:SS)

## Installation

1. Ensure you have Python 3.8+ installed
2. Install Poetry for dependency management
3. Install dependencies:
   ```bash
   poetry install
   ```
4. Install FFmpeg (required for video processing):
   ```bash
   # macOS
   brew install ffmpeg

   # Ubuntu/Debian
   sudo apt-get install ffmpeg
   ```

## Usage

### Quick Start

Using the bash wrapper script:

```bash
# Default: Auto-discover videos and save BOTH highlights and full video
./process_highlights.sh --date 2025-01-13

# Specify videos explicitly (still saves both)
./process_highlights.sh --videos "MAH02309.mp4,MAH02310.mp4" --date 2025-01-13

# Optional: Save only highlights (skip full video)
./process_highlights.sh --date 2025-01-13 --no-save-full-video
```

**Note:** By default, the tool saves two files:
- `final_video.mp4` - Highlights only
- `full_video.mp4` - Complete uncut video

### Direct Python Usage

```bash
# Default: Save both highlights and full video
poetry run python src/main.py --date 2025-01-13

# Save only highlights (skip full video)
poetry run python src/main.py --date 2025-01-13 --no-save-full-video

# Specify videos manually
poetry run python src/main.py --videos "video1.mp4,video2.mp4" --date 2025-01-13
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
FILE_DIR="/Users/username/Dropbox/Indoor football"
IMAGEIO_FFMPEG_EXE="/opt/homebrew/bin/ffmpeg"  # Path to ffmpeg if not in PATH
SAVE_FULL_VIDEO=true  # Default: save full video
BEFORE_GOAL_SECONDS=8  # Seconds before timestamp to include
AFTER_GOAL_SECONDS=4   # Seconds after timestamp to include
```

### Output Files

**By default, two video files are created:**

- **Highlights**: `final_video.mp4` - Contains only the highlight clips based on timestamps
- **Full Video**: `full_video.mp4` - Complete uncut concatenated video from all source files

Both files are saved in the date-specific folder (e.g., `/path/to/videos/2025-01-13/`)

You can disable the full video output using `--no-save-full-video` if you only need highlights.

## File Organization

Expected directory structure:

```
Indoor football/
├── 2025-01-13/
│   ├── MAH02158.mp4
│   ├── MAH02159.mp4
│   ├── MAH02160.mp4
│   ├── splits.csv           # Garmin CSV file (must be named "splits.csv")
│   ├── final_video.mp4      # Generated highlights
│   └── full_video.mp4       # Generated full video (optional)
└── 2025-01-20/
    ├── MAH02161.mp4
    ├── ...
```

## CSV Format

The Garmin CSV file should contain a "Cumulative Time" column with timestamps in HH:MM:SS or MM:SS format:

```csv
"Laps","Time","Cumulative Time","Distance",...
"1","0:06.0","0:06.0","0",...
"2","5:23.1","5:29.1","0.01",...
"3","0:33.4","6:02.5","0.00",...
```

## Command Line Options

- `--date YYYY-MM-DD` (required): Date folder containing videos and CSV
- `--videos "video1.mp4,video2.mp4"` (optional): Comma-separated list of videos
- `--save-full-video`: Save the full uncut video alongside highlights
- `--no-save-full-video`: Only save highlights, skip full video
- `--directory /path/to/base`: Override base directory path
