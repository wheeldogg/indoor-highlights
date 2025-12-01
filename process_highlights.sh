#!/bin/bash

# Indoor Football Highlights Processor
# Convenient script to process highlights with common parameters

set -e  # Exit on any error

# Default values
VIDEOS=""
DATE=""
AUTO_MOVE=false
SAVE_FULL_VIDEO=""
SKIP_HIGHLIGHTS=false

# Function to show usage
show_usage() {
    echo "Usage: $0 --videos \"video1.mp4,video2.mp4\" --date YYYY-MM-DD [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --videos              Comma-separated list of video files (optional, auto-discovers if not provided)"
    echo "  --date                Date in YYYY-MM-DD format"
    echo "  --auto-move           Automatically move output to date directory"
    echo "  --save-full-video     Save the full uncut video alongside highlights"
    echo "  --no-save-full-video  Don't save the full uncut video"
    echo "  --skip-highlights     Skip highlights creation and only produce the full video"
    echo ""
    echo "Examples:"
    echo "  $0 --videos \"MAH02309.mp4,MAH02310.mp4,MAH02311.mp4\" --date 2025-07-28 --save-full-video"
    echo "  $0 --date 2025-07-28  # Auto-discovers all MP4 files in date folder"
    echo ""
    echo "Environment variables can be set in .env file:"
    echo "  BASE_DIRECTORY=/Users/swhelan/Dropbox/Indoor football"
    echo "  BEFORE_GOAL_SECONDS=8"
    echo "  AFTER_GOAL_SECONDS=4"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --videos)
            VIDEOS="$2"
            shift 2
            ;;
        --date)
            DATE="$2"
            shift 2
            ;;
        --auto-move)
            AUTO_MOVE=true
            shift
            ;;
        --save-full-video)
            SAVE_FULL_VIDEO="true"
            shift
            ;;
        --no-save-full-video)
            SAVE_FULL_VIDEO="false"
            shift
            ;;
        --skip-highlights)
            SKIP_HIGHLIGHTS=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$DATE" ]]; then
    echo "Error: Missing required argument: --date"
    show_usage
    exit 1
fi

# Build command
if [[ -n "$VIDEOS" ]]; then
    CMD="poetry run python src/main.py --videos \"$VIDEOS\" --date $DATE"
else
    CMD="poetry run python src/main.py --date $DATE"
fi

if [[ "$AUTO_MOVE" == true ]]; then
    CMD="$CMD --auto-move"
fi

if [[ "$SAVE_FULL_VIDEO" == "true" ]]; then
    CMD="$CMD --save-full-video"
elif [[ "$SAVE_FULL_VIDEO" == "false" ]]; then
    CMD="$CMD --no-save-full-video"
fi

if [[ "$SKIP_HIGHLIGHTS" == true ]]; then
    CMD="$CMD --skip-highlights"
fi

echo "Running: $CMD"
echo ""

# Execute the command
eval $CMD

echo ""
echo "Processing complete!"