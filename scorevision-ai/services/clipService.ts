const CLIP_API_URL = "http://127.0.0.1:8765";

export interface ClipRequest {
  videoPath: string;
  analysis: {
    highlights: Array<{
      timestampSeconds: number;
      displayTime?: string;
      description?: string;
      scoreType?: string;
      intensity?: string;
      playerJerseyNumber?: string;
    }>;
    summary?: string;
  };
  outputDir?: string;
  preSeconds?: number;
  postSeconds?: number;
  makeReel?: boolean;
}

export interface ClipResponse {
  success: boolean;
  numClips: number;
  outputDir: string;
  clips: Array<{
    start: number;
    end: number;
    path: string;
  }>;
  reel: string | null;
  error?: string;
}

export const checkClipServerHealth = async (): Promise<boolean> => {
  try {
    const response = await fetch(`${CLIP_API_URL}/health`, {
      method: "GET",
      signal: AbortSignal.timeout(2000),
    });
    return response.ok;
  } catch {
    return false;
  }
};

export const generateClipsViaAPI = async (request: ClipRequest): Promise<ClipResponse> => {
  const response = await fetch(`${CLIP_API_URL}/clip`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Clip generation failed");
  }

  return data as ClipResponse;
};
