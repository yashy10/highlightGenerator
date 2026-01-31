# Highlight MVP

A local-only tool to generate highlight clips from sports videos using scoring timestamps.

## Requirements

- Python 3.11+
- FFmpeg (with ffprobe)

## Installing FFmpeg

### macOS
```bash
brew install ffmpeg
```

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install ffmpeg
```

### Windows
Download from https://ffmpeg.org/download.html and add to PATH.

### Verify Installation
```bash
ffmpeg -version
ffprobe -version
```

## Setup

1. Create and activate a virtual environment:
```bash
cd highlight_mvp
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies (none required beyond standard library):
```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

Generate highlights from a video and scoresheet:
```bash
python -m highlight_mvp.cli \
  --video /path/to/video.mp4 \
  --scoresheet sample_data/sample_scoresheet.jsonl \
  --out outputs/run1 \
  --pre 6 --post 4 --merge-gap 2 \
  --make-reel true
```

### Generate a Sample Scoresheet

Create a test scoresheet with random timestamps:
```bash
python -m highlight_mvp.cli \
  --make-sample-scoresheet sample_data/test_scoresheet.jsonl \
  --duration 600 \
  -n 12
```

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--video` | (required) | Path to the video file |
| `--scoresheet` | (required) | Path to the JSONL scoresheet |
| `--out` | `outputs` | Output directory |
| `--pre` | `6.0` | Seconds before each event |
| `--post` | `4.0` | Seconds after each event |
| `--merge-gap` | `2.0` | Merge clips if gap is less than this |
| `--min-clip` | `2.0` | Minimum clip duration |
| `--max-clip` | `30.0` | Maximum clip duration |
| `--make-reel` | `true` | Create a concatenated highlight reel |
| `-v, --verbose` | `false` | Enable debug logging |

### Python API

```python
from highlight_mvp import generate_highlights

manifest = generate_highlights(
    video_path="/path/to/video.mp4",
    scoresheet_path="sample_data/sample_scoresheet.jsonl",
    output_dir="outputs/my_highlights",
    pre_seconds=6.0,
    post_seconds=4.0,
    merge_gap_seconds=2.0,
    min_clip_seconds=2.0,
    max_clip_seconds=30.0,
    make_reel=True,
)

print(manifest)
# {
#   "video_path": "...",
#   "video_duration": 600.12,
#   "num_events": 12,
#   "num_clips": 10,
#   "clips": [{"start": 39.23, "end": 49.23, "path": "clips/clip_0001_39230_49230.mp4"}, ...],
#   "reel": "reel/highlights.mp4"
# }
```

## Scoresheet Format

JSONL file with one JSON object per line:

```json
{"t": 45.23, "event": "score", "team": "A", "points": 2}
{"t": 98.67, "event": "score", "team": "B", "points": 3}
```

### Required Fields
- `t`: Timestamp in seconds from video start (number)
- `event`: Must be `"score"` to be included

### Optional Fields
- `team`: Team identifier (`"A"` or `"B"`)
- `points`: Points scored (integer)
- `confidence`: Detection confidence (float 0-1)

### Validation Rules
- Only lines with `event == "score"` are processed
- Invalid JSON lines are skipped with a warning
- Events within 0.35 seconds are deduplicated (earliest kept)

## Output Structure

```
outputs/run1/
  clips/
    clip_0001_39230_49230.mp4
    clip_0002_92670_102670.mp4
    ...
  reel/
    highlights.mp4
  manifest.json
```

## Troubleshooting

### "ffmpeg not found"
Ensure FFmpeg is installed and in your PATH:
```bash
which ffmpeg  # Should show path
ffmpeg -version  # Should show version info
```

### "No valid scoring events found"
Check your scoresheet:
- Each line must be valid JSON
- Each event must have `"event": "score"`
- The `t` field must be a number

### Clips are empty or corrupted
- Verify the video file is not corrupted: `ffprobe /path/to/video.mp4`
- Ensure timestamps are within the video duration
- Try with `--verbose` flag for detailed logging

## License

MIT
