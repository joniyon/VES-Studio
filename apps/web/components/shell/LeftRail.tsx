"use client";

import { useState, type ComponentType } from "react";
import { AlertTriangle, Ban, Hand, Info, Layers, MousePointer2, OctagonAlert, XCircle } from "lucide-react";
import type { Issue } from "@/lib/api";
import { Tip } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { EmptyState, SlideOut } from "./panels";

const railButton = "relative grid size-9 place-items-center rounded-lg text-muted-foreground outline-none transition-colors hover:bg-muted hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 aria-expanded:bg-muted aria-expanded:text-foreground";

const TOOLS: { id: string; label: string; shortcut: string; icon: ComponentType<{ className?: string }> }[] = [
  { id: "select", label: "Select", shortcut: "V", icon: MousePointer2 },
  { id: "exclude", label: "Exclude point", shortcut: "X", icon: Ban },
  { id: "layer", label: "Layer edit", shortcut: "E", icon: Layers },
  { id: "pan", label: "Pan / zoom", shortcut: "Z", icon: Hand },
];

function Badge({ n, tone }: { n: number; tone: "error" | "warning" | "info" }) {
  if (n <= 0) return null;
  const bg = tone === "error" ? "bg-destructive" : tone === "warning" ? "bg-warning" : "bg-info";
  return (
    <span aria-hidden className={cn("absolute -right-0.5 -top-0.5 grid min-w-4 place-items-center rounded-full px-1 font-mono text-[10px] leading-4 text-white", bg)}>{n > 99 ? "99+" : n}</span>
  );
}

function IssueList({ items, empty }: { items: Issue[]; empty: string }) {
  if (!items.length) return <EmptyState>{empty}</EmptyState>;
  return (
    <ul className="grid gap-2">
      {items.map((i, k) => (
        <li key={k} className="flex gap-2 rounded-lg border px-2.5 py-2 text-xs">
          {i.severity === "ERROR" ? <XCircle className="mt-0.5 size-3.5 shrink-0 text-destructive" aria-label="error" />
            : i.severity === "WARNING" ? <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-warning" aria-label="warning" />
            : <Info className="mt-0.5 size-3.5 shrink-0 text-info" aria-label="info" />}
          <span className="min-w-0 flex-1">{i.message}{i.row != null && <span className="ml-1 font-mono text-muted-foreground">row {i.row}</span>}</span>
        </li>
      ))}
    </ul>
  );
}

/** Icon-only tool rail. The four tools are inert in stage 1; Errors and Info open a read-only issue list. */
export function LeftRail({ issues }: { issues: Issue[] }) {
  const [open, setOpen] = useState<"errors" | "info" | null>(null);
  const errors = issues.filter((i) => i.severity === "ERROR");
  const warnings = issues.filter((i) => i.severity === "WARNING");
  const infos = issues.filter((i) => i.severity === "INFO" && i.code !== "SUMMARY");
  const toggle = (k: "errors" | "info") => setOpen((o) => (o === k ? null : k));
  return (
    <>
      <nav aria-label="Tools" className="flex w-12 shrink-0 flex-col items-center gap-1 border-r bg-card py-2 max-md:hidden">
        {TOOLS.map((t) => (
          <Tip key={t.id} label={`${t.label} (coming soon)`} shortcut={t.shortcut} side="right">
            <button type="button" aria-label={t.label} aria-disabled="true" onClick={(e) => e.preventDefault()} className={cn(railButton, "cursor-not-allowed opacity-70", t.id === "select" && "bg-muted text-foreground")}>
              <t.icon className="size-4" />
            </button>
          </Tip>
        ))}
        <span className="my-1 h-px w-6 bg-border" aria-hidden />
        <Tip label="Errors & warnings" side="right">
          <button type="button" aria-label={`Errors and warnings: ${errors.length} errors, ${warnings.length} warnings`} aria-expanded={open === "errors"} aria-controls="rail-errors" onClick={() => toggle("errors")} className={railButton}>
            <OctagonAlert className="size-4" />
            <Badge n={errors.length || warnings.length} tone={errors.length ? "error" : "warning"} />
          </button>
        </Tip>
        <Tip label="Info" side="right">
          <button type="button" aria-label={`Info: ${infos.length} notes`} aria-expanded={open === "info"} aria-controls="rail-info" onClick={() => toggle("info")} className={railButton}>
            <Info className="size-4" />
            <Badge n={infos.length} tone="info" />
          </button>
        </Tip>
      </nav>
      {open === "errors" && (
        <SlideOut id="rail-errors" title="Errors & warnings" onClose={() => setOpen(null)}>
          <IssueList items={[...errors, ...warnings]} empty="No errors or warnings. Process data to run QC." />
        </SlideOut>
      )}
      {open === "info" && (
        <SlideOut id="rail-info" title="Info" onClose={() => setOpen(null)}>
          <IssueList items={infos} empty="No notes yet." />
        </SlideOut>
      )}
    </>
  );
}
