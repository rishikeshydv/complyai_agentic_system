import { Loader2, Sparkles } from "lucide-react"
import { LoadingSkeletons } from "./loading-skeleton"

interface LoadingStateProps {
  count?: number
  fullScreen?: boolean
}

export function LoadingState({ count = 3, fullScreen = false }: LoadingStateProps) {
  const wrapperClass = fullScreen ? "min-h-[50vh] flex items-center" : "";

  return (
    <div className={wrapperClass}>
      <div className="w-full space-y-6">
        <div className="rounded-xl border border-border/60 bg-card/80 p-4 shadow-sm">
          <div className="mb-3 flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-border/60 bg-muted/50">
              <Loader2 className="h-4.5 w-4.5 animate-spin text-accent" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-foreground">Analyzing regulatory obligations</p>
              <p className="text-xs text-muted-foreground">Grounding snippets, ranking relevance, and preparing citations.</p>
            </div>
            <div className="ml-auto hidden items-center gap-1 rounded-full border border-border/60 px-2 py-1 text-[11px] text-muted-foreground md:inline-flex">
              <Sparkles className="h-3.5 w-3.5 text-accent" />
              Live Query
            </div>
          </div>

          <div className="h-2 overflow-hidden rounded-full bg-muted">
            <div className="h-full w-1/3 animate-pulse rounded-full bg-gradient-to-r from-accent/30 via-accent to-accent/30" />
          </div>

          <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
            <span className="rounded-full border border-border/60 bg-muted/40 px-2 py-1">Searching obligations</span>
            <span className="rounded-full border border-border/60 bg-muted/40 px-2 py-1">Resolving excerpts</span>
            <span className="rounded-full border border-border/60 bg-muted/40 px-2 py-1">Formatting evidence</span>
          </div>
        </div>

        <LoadingSkeletons count={count} />
      </div>
    </div>
  )
}
