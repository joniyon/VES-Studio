"use client";

import type { ReactNode } from "react";
import type { Issue } from "@/lib/api";
import { Tabs } from "@/components/ui/tabs";
import { TooltipProvider } from "@/components/ui/tooltip";
import { LeftRail } from "./LeftRail";
import { RightRail } from "./RightRail";
import { StatusPanel, type StatusInfo } from "./StatusPanel";
import { SubBar } from "./SubBar";
import { TopBar } from "./TopBar";
import { ZoomControl } from "./ZoomControl";
import type { StepFlags, StepId } from "./steps";

/**
 * Layout shell: top bar, sub-bar, left/right icon rails, central canvas, floating status and zoom.
 * Owns the Tabs root, so the canvas children are the existing `TabsContent` panels. Wrap in ToastProvider.
 */
export function AppShell({
  tab, onTab, flags, done, projectName, stationId, runLabel, savedAt, issues, status, banners, children,
}: {
  tab: string; onTab: (t: string) => void;
  flags: StepFlags; done: Record<StepId, boolean>;
  projectName: string; stationId: string; runLabel: string | null; savedAt: number | null;
  issues: Issue[]; status: StatusInfo; banners?: ReactNode; children: ReactNode;
}) {
  return (
    <TooltipProvider>
      <Tabs value={tab} onValueChange={(v) => onTab(String(v))} className="h-dvh gap-0 overflow-hidden">
        <TopBar flags={flags} done={done} projectName={projectName} savedAt={savedAt} />
        <SubBar projectName={projectName} stationId={stationId} runLabel={runLabel} />
        <div className="relative flex min-h-0 flex-1">
          <LeftRail issues={issues} />
          <main className="min-w-0 flex-1 overflow-auto" aria-label="Canvas">
            <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 pb-32 pt-4">
              {banners}
              {children}
            </div>
          </main>
          <RightRail />
          <StatusPanel info={status} />
          <ZoomControl />
        </div>
      </Tabs>
    </TooltipProvider>
  );
}
