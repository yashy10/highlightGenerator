#!/usr/bin/env python3
"""
Local API server for video clipping.
The frontend calls this instead of using browser FFmpeg.
"""
from __future__ import annotations

import json
import logging
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import threading

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "highlight_mvp"))

from clip_from_analysis import clip_from_analysis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_PORT = 8765
CORS_ORIGIN = "*"


class ClipAPIHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
    
    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == "/health":
            self._send_json({"status": "ok", "service": "scorevision-clipper"})
        elif parsed.path == "/":
            self._send_json({
                "service": "ScoreVision Clip API",
                "endpoints": {
                    "POST /clip": "Generate clips from analysis",
                    "GET /health": "Health check",
                }
            })
        else:
            self._send_json({"error": "Not found"}, 404)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        
        if parsed.path == "/clip":
            self._handle_clip()
        else:
            self._send_json({"error": "Not found"}, 404)
    
    def _handle_clip(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            
            video_path = data.get("videoPath")
            analysis = data.get("analysis")
            output_dir = data.get("outputDir", "outputs/clips")
            pre_seconds = data.get("preSeconds", 6.0)
            post_seconds = data.get("postSeconds", 4.0)
            make_reel = data.get("makeReel", True)
            
            if not video_path:
                self._send_json({"error": "videoPath is required"}, 400)
                return
            
            if not analysis:
                self._send_json({"error": "analysis is required"}, 400)
                return
            
            if not Path(video_path).exists():
                self._send_json({"error": f"Video not found: {video_path}"}, 400)
                return
            
            logger.info(f"Clipping request: {video_path}")
            logger.info(f"  Highlights: {len(analysis.get('highlights', []))}")
            logger.info(f"  Output: {output_dir}")
            
            manifest = clip_from_analysis(
                analysis=analysis,
                video_path=video_path,
                output_dir=output_dir,
                pre_seconds=pre_seconds,
                post_seconds=post_seconds,
                make_reel=make_reel,
            )
            
            self._send_json({
                "success": True,
                "numClips": manifest.get("num_clips", 0),
                "outputDir": output_dir,
                "clips": manifest.get("clips", []),
                "reel": manifest.get("reel"),
            })
            
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
        except FileNotFoundError as e:
            self._send_json({"error": str(e)}, 400)
        except Exception as e:
            logger.exception("Clip error")
            self._send_json({"error": str(e)}, 500)
    
    def log_message(self, format, *args):
        logger.info(f"{self.address_string()} - {format % args}")


def run_server(port: int = DEFAULT_PORT):
    server = HTTPServer(("127.0.0.1", port), ClipAPIHandler)
    logger.info(f"ScoreVision Clip API running at http://127.0.0.1:{port}")
    logger.info("Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ScoreVision Clip API Server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port (default: {DEFAULT_PORT})")
    args = parser.parse_args()
    
    run_server(args.port)
