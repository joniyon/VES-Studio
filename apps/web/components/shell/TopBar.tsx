"use client";

import { Cloud } from "lucide-react";
import { Stepper } from "./Stepper";
import { ThemeToggle } from "./ThemeToggle";
import type { StepFlags, StepId } from "./steps";

export function TopBar({ flags, done, projectName, savedAt }: {
  flags: StepFlags; done: Record<StepId, boolean>; projectName: string; savedAt: number | null;
}) {
  return (
    <header className="flex h-10 shrink-0 items-center gap-3 border-b bg-card px-3">
      <div className="flex items-center gap-2" aria-label="VES Studio">
        <span className="grid size-5 place-items-center rounded-md bg-primary font-mono text-[10px] font-bold text-primary-foreground">V</span>
        <span className="text-sm font-semibold tracking-tight max-sm:sr-only">VES Studio</span>
      </div>
      <Stepper flags={flags} done={done} />
      <div className="flex items-center gap-3">
        <span className="max-w-48 truncate text-xs text-muted-foreground max-md:hidden" title={projectName}>{projectName || "Untitled project"}</span>
        <span className="flex items-center gap-1 font-mono text-[11px] text-muted-foreground max-lg:hidden" aria-live="polite">
          <Cloud className="size-3.5" aria-hidden />
          {savedAt ? `Autosaved ${new Date(savedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}` : "Autosave on"}
        </span>
        <ThemeToggle />
      </div>
    </header>
  );
}
