import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

type Tone = "neutral" | "good" | "warn" | "bad";
type Variant = "default" | "secondary" | "outline" | "destructive";

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  text?: string;
  children?: ReactNode;
  tone?: Tone;
  variant?: Variant;
};

export function Badge({ text, children, tone, variant = "secondary", className, ...props }: BadgeProps) {
  const resolved = tone || null;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-1 text-xs font-semibold",
        resolved === "neutral" && "bg-slate-100 text-slate-700",
        resolved === "good" && "bg-emerald-100 text-emerald-700",
        resolved === "warn" && "bg-amber-100 text-amber-700",
        resolved === "bad" && "bg-rose-100 text-rose-700",
        !resolved && variant === "default" && "bg-ink text-white",
        !resolved && variant === "secondary" && "bg-slate-100 text-slate-700",
        !resolved && variant === "outline" && "border border-black/15 bg-white text-ink",
        !resolved && variant === "destructive" && "bg-red-700 text-white",
        className,
      )}
      {...props}
    >
      {text ?? children}
    </span>
  );
}
