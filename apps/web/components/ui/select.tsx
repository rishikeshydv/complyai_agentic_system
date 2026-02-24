import type { SelectHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "w-full rounded-md border border-black/20 bg-white px-3 py-2 text-sm outline-none focus:border-clay",
        className,
      )}
      {...props}
    />
  );
}
