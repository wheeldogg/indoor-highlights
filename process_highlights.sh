#!/bin/bash

# Indoor Football Highlights Processor
# Convenient script to process highlights with common parameters

set -e  # Exit on any error

# Default values
VIDEOS=""
CSV=""
DATE=""
AUTO_MOVE=false

# Function to show usage
show_usage() {
    echo "Usage: $0 --videos \"video1.mp4,video2.mp4\" --csv \"path/to/splits.csv\" --date YYYY-MM-DD [--auto-move]"
    echo ""
    echo "Options:"
    echo "  --videos     Comma-separated list of video files"
    echo "  --csv        Path to CSV file with timestamps"
    echo "  --date       Date in YYYY-MM-DD format"
    echo "  --auto-move  Automatically move output to date directory"
    echo ""
    echo "Examples:"
    echo "  $0 --videos \"MAH02309.mp4,MAH02310.mp4,MAH02311.mp4\" --csv \"/Users/swhelan/Dropbox/Indoor football/2025-07-28/splits.csv\" --date 2025-07-28 --auto-move"
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
        --csv)
            CSV="$2"
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
if [[ -z "$VIDEOS" || -z "$CSV" || -z "$DATE" ]]; then
    echo "Error: Missing required arguments"
    show_usage
    exit 1
fi

# Build command
CMD="poetry run python src/main.py --videos \"$VIDEOS\" --csv \"$CSV\" --date $DATE"

if [[ "$AUTO_MOVE" == true ]]; then
    CMD="$CMD --auto-move"
fi

echo "Running: $CMD"
echo ""

# Execute the command
eval $CMD

echo ""
echo "Processing complete!"