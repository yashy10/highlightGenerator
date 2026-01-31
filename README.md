# ScoreVision AI - Highlight Generator

AI-powered sports video highlight detection and clip generation.

## Architecture

```
highlightGenerator/
├── backend/           # FastAPI backend (Cloud Run)
│   ├── routers/       # API endpoints (upload, analyze, clips)
│   └── services/      # GCS, Gemini, FFmpeg services
└── scorevision-ai/    # React frontend (Vite)
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- FFmpeg installed locally
- Google Cloud account (for cloud deployment)
- Gemini API key

## Running Locally

### Backend

```bash
cd backend

# Create environment file
cp .env.example .env

# Edit .env with your credentials:
# - GOOGLE_CLOUD_PROJECT=your-project-id
# - GCS_BUCKET=scorevision-videos
# - GEMINI_API_KEY=your-gemini-api-key

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --reload --port 8080
```

### Frontend

```bash
cd scorevision-ai

# Create environment file (optional, defaults to localhost:8080)
cp .env.example .env.local

# Install dependencies
npm install

# Run the dev server
npm run dev
```

The frontend will be available at `http://localhost:5173`.

## Cloud Deployment

### Deploy Backend to Cloud Run

```bash
cd backend

# Build and push container
gcloud builds submit --tag gcr.io/YOUR_PROJECT/scorevision-api

# Deploy to Cloud Run
gcloud run deploy scorevision-api \
  --image gcr.io/YOUR_PROJECT/scorevision-api \
  --allow-unauthenticated \
  --set-env-vars "GCS_BUCKET=scorevision-videos,GEMINI_API_KEY=your-key"
```

### Deploy Frontend to Vercel

```bash
cd scorevision-ai

# Set the API URL environment variable in Vercel
# VITE_API_URL=https://your-cloud-run-url.run.app/api

vercel deploy
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload video to GCS |
| `/api/analyze/{videoId}` | POST | Analyze video with Gemini AI |
| `/api/analyze/{videoId}` | GET | Get cached analysis |
| `/api/clips/{videoId}` | POST | Generate clips with FFmpeg |
| `/api/clips/{videoId}` | GET | Get generated clips |
| `/api/videos/{videoId}` | GET | Get video info |
| `/health` | GET | Health check |

## Environment Variables

### Backend
| Variable | Description |
|----------|-------------|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID |
| `GCS_BUCKET` | GCS bucket name for video storage |
| `GEMINI_API_KEY` | Gemini API key |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) |

### Frontend
| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend API URL (default: `http://localhost:8080/api`) |