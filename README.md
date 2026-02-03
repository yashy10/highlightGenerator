# Highlight Generator

Auto-generate basketball highlight reels with AI narration.

## What It Does

1. **Upload** a basketball video
2. **YOLO tracking** identifies all players and scores them using 7 signals (motion, acceleration, jumps, size, centrality, persistence, pose dynamism)
3. **Auto-crops** to 9:16 vertical format following the highest-scoring player with a smooth broadcast-style camera
4. **Add Narration** (optional) — uses Gemini to describe the video, GPT to write a sports commentary script, and OpenAI TTS to generate audio, then muxes it onto the video

## Tech Stack

- **Backend**: FastAPI, YOLO11n (ultralytics), OpenCV, supervision, google-genai, openai
- **Frontend**: Next.js 15, React 19, TailwindCSS

## Project Structure

```
highlightGenerator/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Pydantic settings (loads .env)
│   ├── models.py               # Request/response models
│   ├── routers/
│   │   ├── upload.py           # POST /api/upload
│   │   ├── analyze.py          # POST /api/analyze/{videoId}
│   │   ├── clips.py            # GET/POST /api/clips/{videoId}
│   │   └── narration.py        # POST /api/narrate/{videoId}
│   ├── services/
│   │   ├── auto_highlight.py   # YOLO tracking + scoring + rendering
│   │   ├── storage.py          # Local file storage management
│   │   └── narration.py        # Gemini + OpenAI TTS pipeline
│   ├── data/                   # Video/clip storage (gitignored)
│   └── .env                    # API keys (gitignored)
├── frontend/
│   ├── src/
│   │   ├── app/page.tsx        # Main upload/process UI
│   │   └── components/
│   │       ├── video-uploader.tsx
│   │       ├── process-button.tsx
│   │       └── highlight-viewer.tsx  # Video player + narration button
│   └── next.config.ts          # Proxies /api to backend
└── README.md
```

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- ffmpeg (`brew install ffmpeg`)

### Backend

```bash
cd backend

# Install dependencies
pip install fastapi uvicorn pydantic-settings python-multipart \
            ultralytics opencv-python supervision numpy torch \
            google-genai openai python-dotenv

# Create .env with your API keys
cat > .env << EOF
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
EOF

# Run
uvicorn main:app --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend

npm install
npm run dev
```

Open http://localhost:3000

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload video, returns `videoId` |
| `/api/analyze/{videoId}` | POST | Run YOLO tracking, generate highlight |
| `/api/clips/{videoId}` | GET | Get highlight video metadata |
| `/api/narrate/{videoId}` | POST | Add AI narration to highlight |
| `/api/files/{path}` | GET | Serve video/clip files |

## How the Highlight Algorithm Works

### 7-Signal Scoring

For each tracked player, we compute:

| Signal | Weight | Measures |
|--------|--------|----------|
| Motion | 0.25 | Total distance traveled |
| Acceleration | 0.20 | Speed changes (crossovers, drives) |
| Vertical jump | 0.20 | Upward bbox movement (shots, dunks) |
| Size | 0.10 | Bbox area (camera zoom proxy) |
| Centrality | 0.10 | Distance from frame center |
| Persistence | 0.10 | Frames present |
| Aspect ratio variance | 0.05 | Pose dynamism |

The highest-scoring player becomes the target.

### Broadcast Camera

- **EMA smoothing** (alpha=0.04) — prevents jerky panning
- **Dead zone** (9%) — camera doesn't move for small player movements
- **Center gravity** (15%) — gently biases toward frame center
- **Drift back** — returns to center if player disappears

### Output

- 1080x1920 (9:16 vertical, optimized for TikTok/Reels/Shorts)
- Gold spotlight effect on target player
- Original FPS preserved

## Narration Pipeline

1. **ffprobe** — get video duration
2. **Gemini** — upload video and generate detailed description
3. **GPT** — write a sports commentary script (word limit based on duration)
4. **OpenAI TTS** — generate narration audio (voice: coral)
5. **ffmpeg** — mux audio onto video

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | For narration | OpenAI API key |
| `GOOGLE_API_KEY` | For narration | Google AI (Gemini) API key |
| `CORS_ORIGINS` | No | Allowed origins (default: `*`) |
| `STORAGE_DIR` | No | Data directory (default: `./data`) |
