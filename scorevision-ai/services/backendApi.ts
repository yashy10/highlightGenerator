const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8080/api";

export interface UploadResponse {
  videoId: string;
  gcsUrl: string;
  signedUrl: string;
  duration?: number;
}

export interface Highlight {
  timestampSeconds: number;
  displayTime: string;
  description: string;
  scoreType: string;
  intensity: string;
  playerJerseyNumber?: string;
}

export interface AnalyzeResponse {
  highlights: Highlight[];
  summary: string;
  videoId: string;
}

export interface ClipInfo {
  url: string;
  signedUrl: string;
  start: number;
  end: number;
  index: number;
}

export interface ClipsResponse {
  clips: ClipInfo[];
  reelUrl: string | null;
  reelSignedUrl: string | null;
  videoId: string;
}

export interface VideoInfo {
  videoId: string;
  gcsUrl: string;
  signedUrl: string;
  analyzed: boolean;
  hasClips: boolean;
}

export const checkBackendHealth = async (): Promise<boolean> => {
  try {
    const response = await fetch(`${API_BASE_URL.replace('/api', '')}/health`, {
      method: "GET",
      signal: AbortSignal.timeout(3000),
    });
    return response.ok;
  } catch {
    return false;
  }
};

export const uploadVideo = async (
  file: File,
  onProgress?: (progress: number) => void
): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append("file", file);

  const xhr = new XMLHttpRequest();
  
  return new Promise((resolve, reject) => {
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable && onProgress) {
        const progress = Math.round((event.loaded / event.total) * 100);
        onProgress(progress);
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          const error = JSON.parse(xhr.responseText);
          reject(new Error(error.detail || "Upload failed"));
        } catch {
          reject(new Error("Upload failed"));
        }
      }
    });

    xhr.addEventListener("error", () => {
      reject(new Error("Network error during upload"));
    });

    xhr.open("POST", `${API_BASE_URL}/upload`);
    xhr.send(formData);
  });
};

export const analyzeVideo = async (videoId: string): Promise<AnalyzeResponse> => {
  const response = await fetch(`${API_BASE_URL}/analyze/${videoId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Analysis failed" }));
    throw new Error(error.detail || "Analysis failed");
  }

  return response.json();
};

export const getAnalysis = async (videoId: string): Promise<AnalyzeResponse | null> => {
  try {
    const response = await fetch(`${API_BASE_URL}/analyze/${videoId}`, {
      method: "GET",
    });

    if (response.status === 404) {
      return null;
    }

    if (!response.ok) {
      throw new Error("Failed to get analysis");
    }

    return response.json();
  } catch {
    return null;
  }
};

export const generateClips = async (
  videoId: string,
  options: {
    preSeconds?: number;
    postSeconds?: number;
    makeReel?: boolean;
  } = {}
): Promise<ClipsResponse> => {
  const response = await fetch(`${API_BASE_URL}/clips/${videoId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      preSeconds: options.preSeconds ?? 6,
      postSeconds: options.postSeconds ?? 4,
      makeReel: options.makeReel ?? true,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Clip generation failed" }));
    throw new Error(error.detail || "Clip generation failed");
  }

  return response.json();
};

export const getClips = async (videoId: string): Promise<ClipsResponse | null> => {
  try {
    const response = await fetch(`${API_BASE_URL}/clips/${videoId}`, {
      method: "GET",
    });

    if (response.status === 404) {
      return null;
    }

    if (!response.ok) {
      throw new Error("Failed to get clips");
    }

    return response.json();
  } catch {
    return null;
  }
};

export const getVideoInfo = async (videoId: string): Promise<VideoInfo | null> => {
  try {
    const response = await fetch(`${API_BASE_URL}/videos/${videoId}`, {
      method: "GET",
    });

    if (response.status === 404) {
      return null;
    }

    if (!response.ok) {
      throw new Error("Failed to get video info");
    }

    return response.json();
  } catch {
    return null;
  }
};
