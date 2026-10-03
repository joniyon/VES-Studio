"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** Escape closes the panel; focus moves into it on open and back to the opener on close. */
function usePanelFocus(onClose: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  useEffect(() => { close.current = onClose; });
  useEffect(() => {
    const returnTo = document.activeElement;
    ref.current?.querySelector<HTMLElement>("[data-panel-close]")?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close.current(); };
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); if (returnTo instanceof HTMLElement) returnTo.focus(); };
  }, []);
  return ref;
}

function Header({ title, onClose }: { title: string; onClose: () => void }) {
  return (
    <div className="flex items-center justify-between border-b px-3 py-2">
      <h2 className="text-sm font-medium">{title}</h2>
      <Button data-panel-close size="icon-xs" variant="ghost" aria-label={`Close ${title}`} onClick={onClose}><X /></Button>
    </div>
  );
}

/** Floating card opened from the right rail. */
export function FloatingCard({ id, title, onClose, children, className }: { id: string; title: string; onClose: () => void; children: ReactNode; className?: string }) {
  const ref = usePanelFocus(onClose);
  return (
    <div ref={ref} id={id} role="dialog" aria-label={title}
      className={cn("absolute right-14 top-3 z-30 w-72 rounded-xl border bg-popover text-popover-foreground shadow-[var(--shadow-float)] animate-in fade-in-0 slide-in-from-right-2 duration-150", className)}>
      <Header title={title} onClose={onClose} />
      <div className="p-3 text-sm">{children}</div>
    </div>
  );
}

/** Non-modal panel sliding out from the left rail. */
export function SlideOut({ id, title, onClose, children }: { id: string; title: string; onClose: () => void; children: ReactNode }) {
  const ref = usePanelFocus(onClose);
  return (
    <div ref={ref} id={id} role="complementary" aria-label={title}
      className="absolute inset-y-0 left-12 z-30 flex w-80 flex-col border-r bg-popover text-popover-foreground shadow-[var(--shadow-float)] animate-in fade-in-0 slide-in-from-left-2 duration-150">
      <Header title={title} onClose={onClose} />
      <div className="min-h-0 flex-1 overflow-auto p-3 text-sm">{children}</div>
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <p className="rounded-lg border border-dashed px-3 py-6 text-center text-xs text-muted-foreground">{children}</p>;
}
