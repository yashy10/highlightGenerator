"use client"

import { Cog, Play } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"

interface ProcessingSectionProps {
  isProcessing: boolean
  progress: number
  canProcess: boolean
  onProcess: () => void
}

export function ProcessingSection({
  isProcessing,
  progress,
  canProcess,
  onProcess,
}: ProcessingSectionProps) {
  return (
    <Card className="flex h-full flex-col border-border bg-card">
      <CardHeader className="pb-2 pt-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Cog className="h-4 w-4 text-primary" />
          Process
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col justify-center pb-3">
        {isProcessing ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Processing...</span>
              <span className="font-mono text-primary">{progress}%</span>
            </div>
            <Progress value={progress} className="h-2 bg-secondary [&>div]:bg-primary" />
            <p className="text-[10px] text-muted-foreground">
              {progress < 30
                ? "Detecting faces..."
                : progress < 60
                  ? "Finding moments..."
                  : progress < 90
                    ? "Generating clips..."
                    : "Finalizing..."}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <Button
              onClick={onProcess}
              disabled={!canProcess}
              className="w-full bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              size="default"
            >
              <Play className="mr-2 h-4 w-4" />
              Process
            </Button>
            {!canProcess && (
              <p className="text-center text-[10px] text-muted-foreground">
                Upload a video first
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
