"use client";

import { useState } from "react";
import { Download, Info, Mic } from "lucide-react";

interface HighlightResult {
  videoUrl: string;
  targetPlayerId: number;
  score: number;
  duration: number;
  resolution: string;
  fileSizeMb: number;
  summary: string;
}

interface HighlightViewerProps {
  result: HighlightResult | null;
  videoId: string | null;
}

export function HighlightViewer({ result, videoId }: HighlightViewerProps) {
  const [isNarrating, setIsNarrating] = useState(false);
  const [narratedUrl, setNarratedUrl] = useState<string | null>(null);
  const [narrationError, setNarrationError] = useState<string | null>(null);

  if (!result) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-zinc-800 bg-zinc-900 p-12 text-center">
        <Info className="h-8 w-8 text-zinc-600" />
        <p className="text-sm text-zinc-500">
          Upload a video and click Generate to create a highlight
        </p>
      </div>
    );
  }

  const currentVideoUrl = narratedUrl ?? result.videoUrl;

  const handleDownload = () => {
    const a = document.createElement("a");
    a.href = currentVideoUrl;
    a.download = narratedUrl ? "highlight_narrated.mp4" : "highlight.mp4";
    a.click();
  };

  const handleNarrate = async () => {
    if (!videoId) return;
    setIsNarrating(true);
    setNarrationError(null);

    try {
      const res = await fetch(`/api/narrate/${videoId}`, { method: "POST" });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`Narration failed: ${detail}`);
      }
      const data = await res.json();
      setNarratedUrl(data.narratedVideoUrl);
    } catch (err) {
      setNarrationError(
        err instanceof Error ? err.message : "Narration failed"
      );
    } finally {
      setIsNarrating(false);
    }
  };

  const mins = Math.floor(result.duration / 60);
  const secs = Math.floor(result.duration % 60);

  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-xl border border-zinc-800 bg-black">
        <video
          src={currentVideoUrl}
          controls
          key={currentVideoUrl}
          className="mx-auto max-h-[500px]"
        />
      </div>

      <div className="flex items-start justify-between gap-4 rounded-xl border border-zinc-800 bg-zinc-900 p-4">
        <div className="space-y-1 text-sm">
          <p className="font-medium text-zinc-200">
            Player #{result.targetPlayerId} Highlight
            {narratedUrl && (
              <span className="ml-2 text-xs text-emerald-400">with narration</span>
            )}
          </p>
          <p className="text-zinc-500">{result.summary}</p>
          <div className="flex gap-4 pt-1 text-xs text-zinc-500">
            <span>
              {mins}:{secs.toString().padStart(2, "0")}
            </span>
            <span>{result.resolution}</span>
            <span>{result.fileSizeMb} MB</span>
            <span>Score: {result.score.toFixed(3)}</span>
          </div>
        </div>
        <div className="flex shrink-0 gap-2">
          {!narratedUrl && (
            <button
              onClick={handleNarrate}
              disabled={isNarrating}
              className="rounded-lg bg-emerald-800 px-4 py-2 text-sm font-medium text-emerald-100 transition-colors hover:bg-emerald-700 disabled:opacity-50"
            >
              <span className="flex items-center gap-2">
                <Mic className="h-4 w-4" />
                {isNarrating ? "Adding narration..." : "Add Narration"}
              </span>
            </button>
          )}
          <button
            onClick={handleDownload}
            className="rounded-lg bg-zinc-800 px-4 py-2 text-sm font-medium text-zinc-200 transition-colors hover:bg-zinc-700"
          >
            <span className="flex items-center gap-2">
              <Download className="h-4 w-4" />
              Download
            </span>
          </button>
        </div>
      </div>

      {narrationError && (
        <div className="rounded-xl border border-red-900/50 bg-red-950/30 px-4 py-3 text-sm text-red-400">
          {narrationError}
        </div>
      )}
    </div>
  );
}
