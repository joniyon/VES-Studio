"use client";

import { Minus, Plus } from "lucide-react";
import { Tip } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

const btn = "grid size-7 cursor-not-allowed place-items-center rounded-md text-muted-foreground opacity-70 outline-none focus-visible:ring-3 focus-visible:ring-ring/50";

/** Bottom-right zoom control; inert until the canvas tools arrive (charts keep their own Plotly zoom). */
export function ZoomControl() {
  const noop = (e: React.MouseEvent) => e.preventDefault();
  return (
    <div role="group" aria-label="Zoom" className="absolute bottom-3 right-14 z-20 flex items-center gap-0.5 rounded-xl border bg-popover/95 p-1 shadow-[var(--shadow-float)] backdrop-blur max-md:hidden">
      <Tip label="Zoom out (coming soon)" side="top"><button type="button" aria-label="Zoom out" aria-disabled="true" onClick={noop} className={btn}><Minus className="size-3.5" /></button></Tip>
      <span className={cn("w-12 text-center font-mono text-[11px] text-muted-foreground")} aria-label="Zoom level">100%</span>
      <Tip label="Zoom in (coming soon)" side="top"><button type="button" aria-label="Zoom in" aria-disabled="true" onClick={noop} className={btn}><Plus className="size-3.5" /></button></Tip>
    </div>
  );
}
