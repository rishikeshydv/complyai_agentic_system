import { Card } from "@/components/ui/card"

interface LoadingSkeletonsProps {
  count?: number
}

export function LoadingSkeletons({ count = 3 }: LoadingSkeletonsProps) {
  return (
    <div className="space-y-5">
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i} className="overflow-hidden border-border/70 bg-card/90">
          <div className="animate-pulse">
            <div className="border-b border-border/50 bg-gradient-to-r from-muted/40 via-muted/20 to-transparent px-6 py-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-20 rounded-full bg-muted" />
                  <div className="h-5 w-2/3 rounded bg-muted" />
                  <div className="h-4 w-1/2 rounded bg-muted" />
                </div>
                <div className="h-6 w-20 rounded-full bg-muted/90" />
              </div>
            </div>

            <div className="space-y-4 px-6 py-5">
              <div className="space-y-2">
                <div className="h-3 w-24 rounded-full bg-muted" />
                <div className="h-4 w-full rounded bg-muted" />
                <div className="h-4 w-5/6 rounded bg-muted" />
              </div>

              <div className="rounded-lg border border-border/60 p-3">
                <div className="mb-2 h-3 w-28 rounded-full bg-muted" />
                <div className="h-4 w-full rounded bg-muted" />
                <div className="mt-2 h-4 w-4/5 rounded bg-muted" />
              </div>

              <div className="space-y-2">
                <div className="h-3 w-24 rounded-full bg-muted" />
                <div className="h-4 w-full rounded bg-muted" />
                <div className="h-4 w-11/12 rounded bg-muted" />
                <div className="h-4 w-4/5 rounded bg-muted" />
              </div>

              <div className="flex flex-wrap gap-2">
                <div className="h-6 w-20 rounded-full bg-muted" />
                <div className="h-6 w-24 rounded-full bg-muted" />
                <div className="h-6 w-16 rounded-full bg-muted" />
                <div className="h-6 w-28 rounded-full bg-muted" />
              </div>

              <div className="flex items-center justify-between border-t border-border/50 pt-3">
                <div className="h-4 w-36 rounded bg-muted" />
                <div className="flex gap-2">
                  <div className="h-8 w-20 rounded-md bg-muted" />
                  <div className="h-8 w-24 rounded-md bg-muted" />
                </div>
              </div>
            </div>
          </div>
          <div className="h-1 w-full bg-gradient-to-r from-transparent via-accent/30 to-transparent" />
        </Card>
      ))}
    </div>
  )
}
