"use client";

import { useState, useCallback } from "react";
import { VideoUploader } from "@/components/video-uploader";
import { ProcessButton } from "@/components/process-button";
import { HighlightViewer } from "@/components/highlight-viewer";

interface HighlightResult {
  videoUrl: string;
  targetPlayerId: number;
  score: number;
  duration: number;
  resolution: string;
  fileSizeMb: number;
  summary: string;
}

export default function Home() {
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progressPhase, setProgressPhase] = useState("");
  const [result, setResult] = useState<HighlightResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [videoId, setVideoId] = useState<string | null>(null);

  const handleUpload = useCallback((file: File) => {
    setVideoFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setResult(null);
    setError(null);
  }, []);

  const handleClear = useCallback(() => {
    setVideoFile(null);
    setPreviewUrl(null);
    setResult(null);
    setError(null);
    setVideoId(null);
  }, []);

  const handleProcess = useCallback(async () => {
    if (!videoFile) return;

    setIsProcessing(true);
    setError(null);
    setResult(null);

    try {
      // Step 1: Upload
      setProgressPhase("Uploading video...");
      const formData = new FormData();
      formData.append("file", videoFile);

      const uploadRes = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      if (!uploadRes.ok) {
        const detail = await uploadRes.text();
        throw new Error(`Upload failed: ${detail}`);
      }

      const { videoId: uploadedId } = await uploadRes.json();
      setVideoId(uploadedId);

      // Step 2: Analyze (YOLO processing)
      setProgressPhase("Tracking players & generating highlight...");

      const analyzeRes = await fetch(`/api/analyze/${uploadedId}`, {
        method: "POST",
      });

      if (!analyzeRes.ok) {
        const detail = await analyzeRes.text();
        throw new Error(`Analysis failed: ${detail}`);
      }

      const data = await analyzeRes.json();
      const auto = data.autoHighlight;
      const highlightUrl = data.highlightVideoUrl;

      if (!highlightUrl) {
        throw new Error("No highlight video was generated");
      }

      setResult({
        videoUrl: highlightUrl,
        targetPlayerId: auto?.targetPlayerId ?? 0,
        score: auto?.score ?? 0,
        duration: auto?.duration ?? 0,
        resolution: auto?.resolution ?? "",
        fileSizeMb: auto?.fileSizeMb ?? 0,
        summary: data.summary ?? "",
      });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "An unexpected error occurred"
      );
    } finally {
      setIsProcessing(false);
      setProgressPhase("");
    }
  }, [videoFile]);

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <header className="mb-8 text-center">
        <h1 className="text-2xl font-bold tracking-tight">
          Highlight Generator
        </h1>
        <p className="mt-1 text-sm text-zinc-500">
          Upload a basketball video to auto-generate a player highlight reel
        </p>
      </header>

      <div className="space-y-6">
        <VideoUploader
          videoFile={videoFile}
          previewUrl={previewUrl}
          onUpload={handleUpload}
          onClear={handleClear}
        />

        <ProcessButton
          isProcessing={isProcessing}
          canProcess={!!videoFile && !isProcessing}
          progressPhase={progressPhase}
          onProcess={handleProcess}
        />

        {error && (
          <div className="rounded-xl border border-red-900/50 bg-red-950/30 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        <HighlightViewer result={result} videoId={videoId} />
      </div>
    </main>
  );
}
