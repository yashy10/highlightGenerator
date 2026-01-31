"use client"

import React from "react"

import { useState, useCallback, useRef, useEffect } from "react"
import {
  ChevronUp,
  ChevronDown,
  Heart,
  HeartOff,
  Download,
  Play,
  Film,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { Clip } from "@/app/page"

interface ClipFilmstripProps {
  clips: Clip[]
  isProcessed: boolean
  likedCount: number
  onLike: (clipId: string) => void
  onUnlike: (clipId: string) => void
  onDownload: (clipId: string) => void
  onDownloadAllLiked: () => void
  onSelectClip: (clip: Clip) => void
}

export function ClipFilmstrip({
  clips,
  isProcessed,
  likedCount,
  onLike,
  onUnlike,
  onDownload,
  onDownloadAllLiked,
  onSelectClip,
}: ClipFilmstripProps) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)

  const goUp = useCallback(() => {
    setCurrentIndex((prev) => Math.max(0, prev - 1))
  }, [])

  const goDown = useCallback(() => {
    setCurrentIndex((prev) => Math.min(clips.length - 1, prev + 1))
  }, [clips.length])

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowUp") {
        e.preventDefault()
        goUp()
      } else if (e.key === "ArrowDown") {
        e.preventDefault()
        goDown()
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [goUp, goDown])

  // Handle wheel scroll
  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      if (clips.length === 0) return
      if (e.deltaY > 0) {
        goDown()
      } else {
        goUp()
      }
    },
    [clips.length, goUp, goDown]
  )

  if (!isProcessed) {
    return (
      <div className="flex h-full flex-col rounded-lg border border-border bg-card">
        {/* Filmstrip header */}
        <div className="border-b border-border px-3 py-2">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Film className="h-4 w-4 text-primary" />
            Generated Clips
          </h2>
        </div>

        {/* Empty state */}
        <div className="flex flex-1 flex-col items-center justify-center p-4">
          <div className="rounded-full bg-secondary p-4">
            <Film className="h-8 w-8 text-muted-foreground" />
          </div>
          <p className="mt-3 text-center text-xs text-muted-foreground">
            Process a video to generate clips
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-card">
      {/* Filmstrip header */}
      <div className="border-b border-border px-3 py-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <Film className="h-4 w-4 text-primary" />
          Generated Clips
        </h2>
        <p className="mt-0.5 text-[10px] text-muted-foreground">
          {clips.length} clips • {likedCount} liked
        </p>
      </div>

      {/* Navigation Up */}
      <button
        onClick={goUp}
        disabled={currentIndex === 0}
        className="flex items-center justify-center border-b border-border bg-secondary/50 py-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:opacity-30"
        type="button"
      >
        <ChevronUp className="h-5 w-5" />
      </button>

      {/* Filmstrip Container */}
      <div
        ref={containerRef}
        onWheel={handleWheel}
        className="relative flex-1 overflow-hidden"
      >
        {/* Film sprocket holes - left side */}
        <div className="absolute left-0 top-0 z-10 h-full w-6 bg-film-sprocket">
          <div className="flex h-full flex-col items-center justify-around py-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={`left-${i}`}
                className="h-3 w-3 rounded-sm sprocket-hole"
              />
            ))}
          </div>
        </div>

        {/* Film sprocket holes - right side */}
        <div className="absolute right-0 top-0 z-10 h-full w-6 bg-film-sprocket">
          <div className="flex h-full flex-col items-center justify-around py-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={`right-${i}`}
                className="h-3 w-3 rounded-sm sprocket-hole"
              />
            ))}
          </div>
        </div>

        {/* Clips Display - Show 3 clips at a time */}
        <div className="flex h-full flex-col mx-6 py-2 gap-2">
          {[-1, 0, 1].map((offset) => {
            const index = currentIndex + offset
            if (index < 0 || index >= clips.length) {
              return <div key={`empty-${offset}`} className="flex-1" />
            }
            
            const clip = clips[index]
            const isCenter = offset === 0
            const opacity = isCenter ? 1 : 0.5

            return (
              <div
                key={clip.id}
                className="flex flex-1 items-center justify-center"
                style={{ opacity }}
              >
                <div
                  className={cn(
                    "relative w-full overflow-hidden rounded-lg border-2 transition-all duration-300 bg-card",
                    isCenter
                      ? "border-primary shadow-lg shadow-primary/20"
                      : "border-border"
                  )}
                >
                  {/* Clip Thumbnail */}
                  <button
                    type="button"
                    onClick={() => onSelectClip(clip)}
                    className="relative aspect-video w-full bg-secondary transition-opacity hover:opacity-80"
                  >
                    <div className="absolute inset-0 flex items-center justify-center bg-secondary">
                      <div className="flex flex-col items-center gap-1">
                        <div className="rounded-full bg-primary/20 p-2">
                          <Play className="h-5 w-5 text-primary" />
                        </div>
                        <span className="text-xs font-medium text-foreground">
                          Clip {index + 1}
                        </span>
                      </div>
                    </div>

                    {/* Duration badge */}
                    <div className="absolute bottom-1 right-1 rounded bg-background/80 px-1.5 py-0.5 text-[10px] font-mono text-foreground">
                      {clip.duration}
                    </div>

                    {/* Timestamp badge */}
                    <div className="absolute left-1 top-1 rounded bg-background/80 px-1.5 py-0.5 text-[10px] text-muted-foreground">
                      @ {clip.timestamp}
                    </div>

                    {/* Liked indicator */}
                    {clip.liked && (
                      <div className="absolute right-1 top-1">
                        <Heart className="h-4 w-4 fill-primary text-primary" />
                      </div>
                    )}
                  </button>

                  {/* Clip Actions - Only show for center clip */}
                  {isCenter && (
                    <div className="flex items-center justify-center gap-1 border-t border-border bg-secondary/50 p-1.5">
                      {clip.liked ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onUnlike(clip.id)}
                          className="h-7 px-2 text-xs text-muted-foreground hover:text-destructive"
                        >
                          <HeartOff className="mr-1 h-3 w-3" />
                          Unlike
                        </Button>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onLike(clip.id)}
                          className="h-7 px-2 text-xs text-muted-foreground hover:text-primary"
                        >
                          <Heart className="mr-1 h-3 w-3" />
                          Like
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onDownload(clip.id)}
                        className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
                      >
                        <Download className="mr-1 h-3 w-3" />
                        Save
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Navigation Down */}
      <button
        onClick={goDown}
        disabled={currentIndex === clips.length - 1}
        className="flex items-center justify-center border-t border-border bg-secondary/50 py-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:opacity-30"
        type="button"
      >
        <ChevronDown className="h-5 w-5" />
      </button>

      {/* Download All Liked */}
      <div className="border-t border-border p-3">
        <Button
          onClick={onDownloadAllLiked}
          disabled={likedCount === 0}
          size="sm"
          className="w-full bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          <Download className="mr-2 h-4 w-4" />
          Download Liked ({likedCount})
        </Button>
      </div>
    </div>
  )
}
