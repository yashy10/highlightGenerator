"use client";

import { useCallback, useRef, useState } from "react";
import { Upload, Film, X } from "lucide-react";

interface VideoUploaderProps {
  videoFile: File | null;
  previewUrl: string | null;
  onUpload: (file: File) => void;
  onClear: () => void;
}

export function VideoUploader({
  videoFile,
  previewUrl,
  onUpload,
  onClear,
}: VideoUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file?.type.startsWith("video/")) {
        onUpload(file);
      }
    },
    [onUpload]
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onUpload(file);
    },
    [onUpload]
  );

  if (videoFile && previewUrl) {
    return (
      <div className="relative rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden">
        <button
          onClick={onClear}
          className="absolute top-3 right-3 z-10 rounded-full bg-zinc-900/80 p-1.5 hover:bg-zinc-800 transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
        <video
          src={previewUrl}
          controls
          className="w-full max-h-[300px] object-contain bg-black"
        />
        <div className="px-4 py-2 border-t border-zinc-800 flex items-center gap-2 text-sm text-zinc-400">
          <Film className="h-4 w-4" />
          {videoFile.name}
          <span className="ml-auto">
            {(videoFile.size / (1024 * 1024)).toFixed(1)} MB
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-12 cursor-pointer transition-colors ${
        isDragging
          ? "border-blue-500 bg-blue-500/10"
          : "border-zinc-700 bg-zinc-900 hover:border-zinc-600 hover:bg-zinc-900/80"
      }`}
    >
      <Upload className="h-10 w-10 text-zinc-500" />
      <div className="text-center">
        <p className="text-sm font-medium text-zinc-300">
          Drop a video here or click to browse
        </p>
        <p className="mt-1 text-xs text-zinc-500">MP4, MOV, AVI supported</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="video/*"
        onChange={handleFileChange}
        className="hidden"
      />
    </div>
  );
}
