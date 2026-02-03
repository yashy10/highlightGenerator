"use client";

import { Play, Loader2 } from "lucide-react";

interface ProcessButtonProps {
  isProcessing: boolean;
  canProcess: boolean;
  progressPhase: string;
  onProcess: () => void;
}

export function ProcessButton({
  isProcessing,
  canProcess,
  progressPhase,
  onProcess,
}: ProcessButtonProps) {
  if (isProcessing) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <p className="text-sm font-medium text-zinc-300">{progressPhase}</p>
        <p className="text-xs text-zinc-500">
          This may take a few minutes for longer videos
        </p>
      </div>
    );
  }

  return (
    <button
      onClick={onProcess}
      disabled={!canProcess}
      className="w-full rounded-xl bg-blue-600 px-6 py-4 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-blue-600"
    >
      <span className="flex items-center justify-center gap-2">
        <Play className="h-5 w-5" />
        Generate Highlight
      </span>
    </button>
  );
}
