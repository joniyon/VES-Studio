"use client";

import { Check } from "lucide-react";
import { TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tip } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { STEPS, lockHint, type StepFlags, type StepId } from "./steps";

/** The seven workflow tabs. Must render inside the shell's Tabs root. */
export function Stepper({ flags, done }: { flags: StepFlags; done: Record<StepId, boolean> }) {
  return (
    <TabsList variant="line" aria-label="Workflow" className="h-10 w-auto min-w-0 flex-1 justify-start gap-0.5 overflow-x-auto p-0">
      {STEPS.map((s) => {
        const hint = lockHint(s.id, flags);
        const trigger = (
          <TabsTrigger
            value={s.id} disabled={hint != null}
            className="h-10 flex-none rounded-md px-2.5 text-[13px] after:bottom-0"
          >
            <span className="font-mono text-xs text-muted-foreground">{s.n}</span>
            <span className="max-lg:sr-only">{s.label}</span>
            {done[s.id] && <Check className="size-3.5 text-success" aria-label="completed" />}
          </TabsTrigger>
        );
        if (!hint) return <span key={s.id} className="flex">{trigger}</span>;
        // a disabled tab cannot take focus or hover, so a focusable wrapper carries the explanation
        return (
          <Tip key={s.id} label={hint}>
            <span tabIndex={0} aria-label={`${s.label}, locked. ${hint}`} className={cn("flex rounded-md outline-none focus-visible:ring-3 focus-visible:ring-ring/50")}>
              {trigger}
            </span>
          </Tip>
        );
      })}
    </TabsList>
  );
}
