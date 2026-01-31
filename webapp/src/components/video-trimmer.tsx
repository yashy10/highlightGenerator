"use client"

import React, { useState, useCallback, useRef, useEffect } from "react"
import { X, Save, RotateCcw, Play, Pause } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { Clip } from "@/app/page"

interface VideoTrimmerProps {
  clip: Clip
  onSave: (clipId: string, trimStart: number, trimEnd: number) => void
  onClose: () => void
}

export function VideoTrimmer({ clip, onSave, onClose }: VideoTrimmerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const timelineRef = useRef<HTMLDivElement>(null)
  const [duration, setDuration] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [trimStart, setTrimStart] = useState(clip.trimStart ?? 0)
  const [trimEnd, setTrimEnd] = useState(clip.trimEnd ?? 0)
  const [isDragging, setIsDragging] = useState<"start" | "end" | null>(null)
  const [hasChanges, setHasChanges] = useState(false)

  // Initialize trim values when video metadata loads
  const handleLoadedMetadata = useCallback(() => {
    const video = videoRef.current
    if (!video) return
    
    const videoDuration = video.duration
    setDuration(videoDuration)
    
    // Initialize trim points
    const initialStart = clip.trimStart ?? 0
    const initialEnd = clip.trimEnd ?? videoDuration
    setTrimStart(initialStart)
    setTrimEnd(initialEnd)
    
    // Start playing from trim start
    video.currentTime = initialStart
  }, [clip.trimStart, clip.trimEnd])

  // Update current time during playback
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const handleTimeUpdate = () => {
      const time = video.currentTime
      setCurrentTime(time)
      
      // Loop within trim range
      if (time >= trimEnd) {
        video.currentTime = trimStart
      }
    }

    video.addEventListener("timeupdate", handleTimeUpdate)
    return () => video.removeEventListener("timeupdate", handleTimeUpdate)
  }, [trimStart, trimEnd])

  // Handle play/pause
  const togglePlayPause = useCallback(() => {
    const video = videoRef.current
    if (!video) return

    if (isPlaying) {
      video.pause()
    } else {
      // If current time is outside trim range, start from trim start
      if (video.currentTime < trimStart || video.currentTime >= trimEnd) {
        video.currentTime = trimStart
      }
      video.play()
    }
    setIsPlaying(!isPlaying)
  }, [isPlaying, trimStart, trimEnd])

  // Calculate position percentage
  const getPositionPercent = useCallback((time: number) => {
    if (duration === 0) return 0
    return (time / duration) * 100
  }, [duration])

  // Calculate time from position
  const getTimeFromPosition = useCallback((clientX: number) => {
    const timeline = timelineRef.current
    if (!timeline || duration === 0) return 0
    
    const rect = timeline.getBoundingClientRect()
    const x = Math.max(0, Math.min(clientX - rect.left, rect.width))
    const percent = x / rect.width
    return percent * duration
  }, [duration])

  // Handle drag start
  const handleDragStart = useCallback((handle: "start" | "end") => (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault()
    setIsDragging(handle)
  }, [])

  // Handle drag move
  useEffect(() => {
    if (!isDragging) return

    const handleMove = (clientX: number) => {
      const time = getTimeFromPosition(clientX)
      
      if (isDragging === "start") {
        // Ensure start doesn't go past end - 0.5s minimum
        const newStart = Math.min(time, trimEnd - 0.5)
        setTrimStart(Math.max(0, newStart))
        setHasChanges(true)
        
        // Update video position to show the new start point
        if (videoRef.current) {
          videoRef.current.currentTime = Math.max(0, newStart)
        }
      } else if (isDragging === "end") {
        // Ensure end doesn't go before start + 0.5s minimum
        const newEnd = Math.max(time, trimStart + 0.5)
        setTrimEnd(Math.min(duration, newEnd))
        setHasChanges(true)
        
        // Update video position to show the new end point
        if (videoRef.current) {
          videoRef.current.currentTime = Math.min(duration, newEnd) - 0.1
        }
      }
    }

    const handleMouseMove = (e: MouseEvent) => handleMove(e.clientX)
    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length > 0) {
        handleMove(e.touches[0].clientX)
      }
    }

    const handleEnd = () => setIsDragging(null)

    document.addEventListener("mousemove", handleMouseMove)
    document.addEventListener("mouseup", handleEnd)
    document.addEventListener("touchmove", handleTouchMove)
    document.addEventListener("touchend", handleEnd)

    return () => {
      document.removeEventListener("mousemove", handleMouseMove)
      document.removeEventListener("mouseup", handleEnd)
      document.removeEventListener("touchmove", handleTouchMove)
      document.removeEventListener("touchend", handleEnd)
    }
  }, [isDragging, getTimeFromPosition, trimStart, trimEnd, duration])

  // Format time as MM:SS
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }

  // Handle save
  const handleSave = useCallback(() => {
    onSave(clip.id, trimStart, trimEnd)
    onClose()
  }, [clip.id, trimStart, trimEnd, onSave, onClose])

  // Handle discard
  const handleDiscard = useCallback(() => {
    onClose()
  }, [onClose])

  // Calculate trim duration
  const trimDuration = trimEnd - trimStart

  return (
    <div className="flex flex-col">
      {/* Video Player */}
      <div className="relative bg-black flex items-center justify-center">
        <video
          ref={videoRef}
          src={clip.videoUrl}
          className="max-h-[280px] w-auto max-w-full"
          onLoadedMetadata={handleLoadedMetadata}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
        >
          <track kind="captions" />
        </video>
        
        {/* Play/Pause overlay */}
        <button
          type="button"
          onClick={togglePlayPause}
          className="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 transition-opacity hover:opacity-100"
        >
          <div className="rounded-full bg-white/90 p-4">
            {isPlaying ? (
              <Pause className="h-8 w-8 text-gray-900" />
            ) : (
              <Play className="h-8 w-8 text-gray-900 ml-1" />
            )}
          </div>
        </button>
      </div>

      {/* Trimmer Controls */}
      <div className="shrink-0 border-t border-border bg-card p-4">
        {/* Timeline */}
        <div className="mb-4">
          <div
            ref={timelineRef}
            className="relative h-12 rounded-lg bg-secondary overflow-hidden cursor-pointer"
          >
            {/* Full timeline background */}
            <div className="absolute inset-0 bg-muted" />
            
            {/* Trimmed region (highlighted) */}
            <div
              className="absolute top-0 bottom-0 bg-primary/30"
              style={{
                left: `${getPositionPercent(trimStart)}%`,
                width: `${getPositionPercent(trimEnd) - getPositionPercent(trimStart)}%`,
              }}
            />

            {/* Left handle (start) */}
            <div
              className="absolute top-0 bottom-0 w-4 cursor-ew-resize touch-none select-none"
              style={{ left: `calc(${getPositionPercent(trimStart)}% - 8px)` }}
              onMouseDown={handleDragStart("start")}
              onTouchStart={handleDragStart("start")}
            >
              <div className="absolute left-1/2 top-0 bottom-0 w-1 -translate-x-1/2 bg-primary rounded-l-sm" />
              <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-6 w-3 rounded-sm bg-primary flex items-center justify-center">
                <div className="w-0.5 h-3 bg-primary-foreground rounded-full" />
              </div>
            </div>

            {/* Right handle (end) */}
            <div
              className="absolute top-0 bottom-0 w-4 cursor-ew-resize touch-none select-none"
              style={{ left: `calc(${getPositionPercent(trimEnd)}% - 8px)` }}
              onMouseDown={handleDragStart("end")}
              onTouchStart={handleDragStart("end")}
            >
              <div className="absolute left-1/2 top-0 bottom-0 w-1 -translate-x-1/2 bg-primary rounded-r-sm" />
              <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-6 w-3 rounded-sm bg-primary flex items-center justify-center">
                <div className="w-0.5 h-3 bg-primary-foreground rounded-full" />
              </div>
            </div>

            {/* Current playhead */}
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-white shadow-lg pointer-events-none"
              style={{ left: `${getPositionPercent(currentTime)}%` }}
            >
              <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-white" />
            </div>

            {/* Greyed out regions (outside trim) */}
            <div
              className="absolute top-0 bottom-0 left-0 bg-black/50 pointer-events-none"
              style={{ width: `${getPositionPercent(trimStart)}%` }}
            />
            <div
              className="absolute top-0 bottom-0 right-0 bg-black/50 pointer-events-none"
              style={{ width: `${100 - getPositionPercent(trimEnd)}%` }}
            />
          </div>

          {/* Time labels */}
          <div className="mt-2 flex justify-between text-xs text-muted-foreground">
            <span>{formatTime(trimStart)}</span>
            <span className="text-foreground font-medium">
              Duration: {formatTime(trimDuration)}
            </span>
            <span>{formatTime(trimEnd)}</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={togglePlayPause}
              className="h-9"
            >
              {isPlaying ? (
                <>
                  <Pause className="mr-1 h-4 w-4" />
                  Pause
                </>
              ) : (
                <>
                  <Play className="mr-1 h-4 w-4" />
                  Play
                </>
              )}
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleDiscard}
              className="h-9"
            >
              <X className="mr-1 h-4 w-4" />
              {hasChanges ? "Discard" : "Close"}
            </Button>
            {hasChanges && (
              <Button
                size="sm"
                onClick={handleSave}
                className="h-9 bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <Save className="mr-1 h-4 w-4" />
                Save Trim
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
