"use client"

import React from "react"

import { useCallback, useRef } from "react"
import { Upload, Film, X, Scissors } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { VideoTrimmer } from "@/components/video-trimmer"
import type { Clip } from "@/app/page"

interface VideoUploaderProps {
  videoPreviewUrl: string | null
  selectedClip: Clip | null
  onUpload: (file: File) => void
  onClearClip: () => void
  onSaveTrim?: (clipId: string, trimStart: number, trimEnd: number) => void
}

export function VideoUploader({ 
  videoPreviewUrl, 
  selectedClip, 
  onUpload, 
  onClearClip,
  onSaveTrim 
}: VideoUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      const file = e.dataTransfer.files[0]
      if (file && file.type.startsWith("video/")) {
        onUpload(file)
      }
    },
    [onUpload]
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
  }, [])

  const handleClick = useCallback(() => {
    inputRef.current?.click()
  }, [])

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) {
        onUpload(file)
      }
    },
    [onUpload]
  )

  const handleSaveTrim = useCallback((clipId: string, trimStart: number, trimEnd: number) => {
    if (onSaveTrim) {
      onSaveTrim(clipId, trimStart, trimEnd)
    }
  }, [onSaveTrim])

  return (
    <Card className="flex-1 border-border bg-card">
      <CardHeader className="pb-2 pt-3">
        <CardTitle className="flex items-center justify-between text-sm">
          <span className="flex items-center gap-2">
            {selectedClip ? (
              <Scissors className="h-4 w-4 text-primary" />
            ) : (
              <Film className="h-4 w-4 text-primary" />
            )}
            {selectedClip ? `Editing: Clip ${selectedClip.id.split('-')[1]}` : 'Video Source'}
          </span>
          {selectedClip && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearClip}
              className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="pb-3">
        <div
          onClick={selectedClip ? undefined : handleClick}
          onDrop={selectedClip ? undefined : handleDrop}
          onDragOver={selectedClip ? undefined : handleDragOver}
          className={`relative w-full overflow-hidden rounded-lg border-2 ${
            selectedClip 
              ? 'border-primary bg-card' 
              : 'cursor-pointer border-dashed border-border bg-secondary/50 transition-colors hover:border-primary hover:bg-secondary min-h-[200px]'
          }`}
        >
          {selectedClip ? (
            <VideoTrimmer
              clip={selectedClip}
              onSave={handleSaveTrim}
              onClose={onClearClip}
            />
          ) : videoPreviewUrl ? (
            <video
              src={videoPreviewUrl}
              controls
              className="h-full w-full object-contain min-h-[200px]"
            >
              <track kind="captions" />
            </video>
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
              <div className="rounded-full bg-secondary p-3">
                <Upload className="h-6 w-6 text-muted-foreground" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-foreground">
                  Drop your video here
                </p>
                <p className="text-xs text-muted-foreground">
                  or click to browse
                </p>
              </div>
            </div>
          )}
          <input
            ref={inputRef}
            type="file"
            accept="video/*"
            onChange={handleChange}
            className="hidden"
          />
        </div>
      </CardContent>
    </Card>
  )
}
