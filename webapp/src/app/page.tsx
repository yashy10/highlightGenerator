"use client"

import { useState, useCallback } from "react"
import { VideoUploader } from "@/components/video-uploader"
import { TargetPlayer } from "@/components/target-player"
import { ProcessingSection } from "@/components/processing-section"
import { ClipFilmstrip } from "@/components/clip-filmstrip"
import { ThemeToggle } from "@/components/theme-toggle"

export interface Clip {
  id: string
  thumbnail: string
  duration: string
  timestamp: string
  liked: boolean
  videoUrl?: string
  trimStart?: number // Start time in seconds
  trimEnd?: number   // End time in seconds
  originalDuration?: number // Original duration in seconds
}

// Mock test clips for development
const MOCK_CLIPS: Clip[] = [
  { id: "clip-1", thumbnail: "", duration: "0:12", timestamp: "2:34", liked: false, videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4" },
  { id: "clip-2", thumbnail: "", duration: "0:08", timestamp: "5:12", liked: false, videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4" },
  { id: "clip-3", thumbnail: "", duration: "0:15", timestamp: "8:45", liked: false, videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4" },
  { id: "clip-4", thumbnail: "", duration: "0:22", timestamp: "12:03", liked: false, videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4" },
  { id: "clip-5", thumbnail: "", duration: "0:18", timestamp: "15:27", liked: false, videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4" },
  { id: "clip-6", thumbnail: "", duration: "0:11", timestamp: "19:50", liked: false, videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4" },
]

export default function Home() {
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [videoPreviewUrl, setVideoPreviewUrl] = useState<string | null>(null)
  const [faceImage, setFaceImage] = useState<File | null>(null)
  const [facePreviewUrl, setFacePreviewUrl] = useState<string | null>(null)
  const [playerName, setPlayerName] = useState("")
  const [jerseyNumber, setJerseyNumber] = useState("")
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [clips, setClips] = useState<Clip[]>(MOCK_CLIPS)
  const [isProcessed, setIsProcessed] = useState(true)
  const [selectedClip, setSelectedClip] = useState<Clip | null>(null)

  const handleVideoUpload = useCallback((file: File) => {
    setVideoFile(file)
    const url = URL.createObjectURL(file)
    setVideoPreviewUrl(url)
    setIsProcessed(false)
    setClips([])
  }, [])

  const handleFaceUpload = useCallback((file: File) => {
    setFaceImage(file)
    const url = URL.createObjectURL(file)
    setFacePreviewUrl(url)
  }, [])

  const handleProcess = useCallback(() => {
    if (!videoFile) return
    
    setIsProcessing(true)
    setProgress(0)
    
    // Simulate processing with progress
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval)
          setIsProcessing(false)
          setIsProcessed(true)
          // Generate mock clips
          const mockClips: Clip[] = Array.from({ length: 8 }, (_, i) => ({
            id: `clip-${i + 1}`,
            thumbnail: `/api/placeholder/320/180?text=Clip ${i + 1}`,
            duration: `0:${String(Math.floor(Math.random() * 30) + 10).padStart(2, "0")}`,
            timestamp: `${Math.floor(Math.random() * 60)}:${String(Math.floor(Math.random() * 60)).padStart(2, "0")}`,
            liked: false,
          }))
          setClips(mockClips)
          return 100
        }
        return prev + 2
      })
    }, 100)
  }, [videoFile])

  const handleLikeClip = useCallback((clipId: string) => {
    setClips((prev) =>
      prev.map((clip) =>
        clip.id === clipId ? { ...clip, liked: true } : clip
      )
    )
  }, [])

  const handleUnlikeClip = useCallback((clipId: string) => {
    setClips((prev) =>
      prev.map((clip) =>
        clip.id === clipId ? { ...clip, liked: false } : clip
      )
    )
  }, [])

  const handleDownloadClip = useCallback((clipId: string) => {
    // Simulate download
    console.log("[v0] Downloading clip:", clipId)
    alert(`Downloading clip ${clipId}`)
  }, [])

  const handleDownloadAllLiked = useCallback(() => {
    const likedClips = clips.filter((clip) => clip.liked)
    if (likedClips.length === 0) {
      alert("No liked clips to download")
      return
    }
    console.log("[v0] Downloading all liked clips:", likedClips.map(c => c.id))
    alert(`Downloading ${likedClips.length} liked clips`)
  }, [clips])

  const handleSelectClip = useCallback((clip: Clip) => {
    setSelectedClip(clip)
  }, [])

  const handleClearSelectedClip = useCallback(() => {
    setSelectedClip(null)
  }, [])

  const handleSaveTrim = useCallback((clipId: string, trimStart: number, trimEnd: number) => {
    setClips((prev) =>
      prev.map((clip) => {
        if (clip.id === clipId) {
          // Calculate new duration string
          const durationSeconds = trimEnd - trimStart
          const mins = Math.floor(durationSeconds / 60)
          const secs = Math.floor(durationSeconds % 60)
          const newDuration = `${mins}:${secs.toString().padStart(2, "0")}`
          
          return {
            ...clip,
            trimStart,
            trimEnd,
            duration: newDuration,
          }
        }
        return clip
      })
    )
    // Update selected clip as well
    setSelectedClip((prev) => {
      if (prev && prev.id === clipId) {
        const durationSeconds = trimEnd - trimStart
        const mins = Math.floor(durationSeconds / 60)
        const secs = Math.floor(durationSeconds % 60)
        const newDuration = `${mins}:${secs.toString().padStart(2, "0")}`
        return {
          ...prev,
          trimStart,
          trimEnd,
          duration: newDuration,
        }
      }
      return prev
    })
  }, [])

  const likedCount = clips.filter((clip) => clip.liked).length

  return (
    <main className="flex h-screen flex-col overflow-hidden bg-background">
      <header className="shrink-0 border-b border-border bg-card">
        <div className="flex items-center justify-between px-6 py-3">
          <div>
            <h1 className="text-xl font-bold tracking-tight">
              <span className="text-[#0057e7]">C</span>
              <span className="text-[#d62d20]">l</span>
              <span className="text-[#ffa700]">i</span>
              <span className="text-[#0057e7]">p</span>
              <span className="text-[#008744]">p</span>
              <span className="text-[#d62d20]">3</span>
            </h1>
            <p className="text-xs text-muted-foreground">Player Highlight Generator</p>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <div className="flex flex-1 gap-6 overflow-hidden p-4">
        {/* Left Section - Upload & Controls */}
        <div className="flex w-[55%] flex-col gap-4">
          <VideoUploader
            videoPreviewUrl={videoPreviewUrl}
            selectedClip={selectedClip}
            onUpload={handleVideoUpload}
            onClearClip={handleClearSelectedClip}
            onSaveTrim={handleSaveTrim}
          />

          <div className="flex gap-4">
            <div className="flex-1">
              <TargetPlayer
                facePreviewUrl={facePreviewUrl}
                playerName={playerName}
                jerseyNumber={jerseyNumber}
                onFaceUpload={handleFaceUpload}
                onPlayerNameChange={setPlayerName}
                onJerseyNumberChange={setJerseyNumber}
              />
            </div>
            <div className="w-[200px]">
              <ProcessingSection
                isProcessing={isProcessing}
                progress={progress}
                canProcess={!!videoFile}
                onProcess={handleProcess}
              />
            </div>
          </div>
        </div>

        {/* Right Section - Clip Filmstrip */}
        <div className="flex-1">
          <ClipFilmstrip
            clips={clips}
            isProcessed={isProcessed}
            likedCount={likedCount}
            onLike={handleLikeClip}
            onUnlike={handleUnlikeClip}
            onDownload={handleDownloadClip}
            onDownloadAllLiked={handleDownloadAllLiked}
            onSelectClip={handleSelectClip}
          />
        </div>
      </div>
    </main>
  )
}
