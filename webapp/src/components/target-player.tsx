"use client"

import React from "react"

import { useCallback, useRef } from "react"
import { User, Upload, Hash, Type } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface TargetPlayerProps {
  facePreviewUrl: string | null
  playerName: string
  jerseyNumber: string
  onFaceUpload: (file: File) => void
  onPlayerNameChange: (name: string) => void
  onJerseyNumberChange: (number: string) => void
}

export function TargetPlayer({
  facePreviewUrl,
  playerName,
  jerseyNumber,
  onFaceUpload,
  onPlayerNameChange,
  onJerseyNumberChange,
}: TargetPlayerProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      const file = e.dataTransfer.files[0]
      if (file && file.type.startsWith("image/")) {
        onFaceUpload(file)
      }
    },
    [onFaceUpload]
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
        onFaceUpload(file)
      }
    },
    [onFaceUpload]
  )

  return (
    <Card className="h-full border-border bg-card">
      <CardHeader className="pb-2 pt-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <User className="h-4 w-4 text-primary" />
          Target Player
        </CardTitle>
      </CardHeader>
      <CardContent className="pb-3">
        <div className="flex gap-3">
          {/* Face Photo Upload */}
          <div
            onClick={handleClick}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            className="h-[80px] w-[80px] shrink-0 cursor-pointer overflow-hidden rounded-lg border-2 border-dashed border-border bg-secondary/50 transition-colors hover:border-primary hover:bg-secondary"
          >
            {facePreviewUrl ? (
              <img
                src={facePreviewUrl || "/placeholder.svg"}
                alt="Player face"
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full flex-col items-center justify-center gap-1 p-2">
                <Upload className="h-5 w-5 text-muted-foreground" />
                <span className="text-center text-[10px] text-muted-foreground">
                  Face
                </span>
              </div>
            )}
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              onChange={handleChange}
              className="hidden"
            />
          </div>

          {/* Player Details */}
          <div className="flex flex-1 flex-col gap-2">
            <div className="space-y-1">
              <Label
                htmlFor="playerName"
                className="flex items-center gap-1.5 text-xs text-muted-foreground"
              >
                <Type className="h-3 w-3" />
                Name (jersey)
              </Label>
              <Input
                id="playerName"
                placeholder="e.g. JOHNSON"
                value={playerName}
                onChange={(e) => onPlayerNameChange(e.target.value)}
                className="h-8 border-border bg-secondary text-sm text-foreground placeholder:text-muted-foreground"
              />
            </div>
            <div className="space-y-1">
              <Label
                htmlFor="jerseyNumber"
                className="flex items-center gap-1.5 text-xs text-muted-foreground"
              >
                <Hash className="h-3 w-3" />
                Number
              </Label>
              <Input
                id="jerseyNumber"
                placeholder="e.g. 23"
                value={jerseyNumber}
                onChange={(e) => onJerseyNumberChange(e.target.value)}
                className="h-8 border-border bg-secondary text-sm text-foreground placeholder:text-muted-foreground"
              />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
