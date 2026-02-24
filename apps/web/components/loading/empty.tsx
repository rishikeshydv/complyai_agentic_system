import { BookOpenText, Search, SlidersHorizontal } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

export function EmptyState() {
  const examples = [
    "31 CFR 1020.320",
    "N.J.A.C. 3:15",
    "OFAC screening",
    "AML compliance program",
  ];

  return (
    <Card className="relative overflow-hidden border-border/70 bg-gradient-to-br from-background via-background to-muted/40 p-8 md:p-10">
      <div className="absolute -right-10 -top-10 h-28 w-28 rounded-full bg-accent/10 blur-2xl" />
      <div className="absolute -left-12 bottom-0 h-24 w-24 rounded-full bg-primary/10 blur-2xl" />

      <div className="relative">
        <div className="mb-5 flex justify-center">
          <div className="rounded-2xl border border-border/60 bg-card/80 p-3 shadow-sm">
            <Search className="h-7 w-7 text-accent" />
          </div>
        </div>

        <h3 className="mb-2 text-center text-xl font-semibold text-foreground">No matching obligations found</h3>
        <p className="mx-auto mb-6 max-w-xl text-center text-sm text-muted-foreground">
          Your current query and filters did not return grounded law obligations. Try broader terms or remove one
          filter at a time.
        </p>

        <div className="mx-auto mb-4 flex max-w-2xl flex-wrap justify-center gap-2">
          {examples.map((example) => (
            <Badge
              key={example}
              variant="secondary"
              className="rounded-full border border-border/60 bg-card px-3 py-1 text-[11px] font-medium tracking-wide text-foreground"
            >
              {example}
            </Badge>
          ))}
        </div>

        <div className="mx-auto grid max-w-2xl gap-3 md:grid-cols-2">
          <div className="rounded-xl border border-border/60 bg-card/70 p-3 text-left">
            <p className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-foreground">
              <SlidersHorizontal className="h-3.5 w-3.5 text-accent" />
              Filter Strategy
            </p>
            <p className="text-xs text-muted-foreground">Clear jurisdiction/agency filters first, then re-run search.</p>
          </div>
          <div className="rounded-xl border border-border/60 bg-card/70 p-3 text-left">
            <p className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-foreground">
              <BookOpenText className="h-3.5 w-3.5 text-accent" />
              Query Strategy
            </p>
            <p className="text-xs text-muted-foreground">Use legal terms, citations, or obligation verbs like file, retain, screen.</p>
          </div>
        </div>
      </div>
    </Card>
  )
}
