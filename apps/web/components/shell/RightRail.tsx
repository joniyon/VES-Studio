"use client";

import { useState, type ComponentType } from "react";
import { Paperclip, Settings2, SlidersHorizontal } from "lucide-react";
import { Tip } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { EmptyState, FloatingCard } from "./panels";

const CARDS: { id: string; label: string; icon: ComponentType<{ className?: string }>; empty: string }[] = [
  { id: "view", label: "View controls", icon: SlidersHorizontal, empty: "Layer and overlay toggles will appear here." },
  { id: "config", label: "Configuration", icon: Settings2, empty: "Inversion and data-preparation settings will appear here." },
  { id: "attachments", label: "Attachments", icon: Paperclip, empty: "The uploaded file and project attachments will appear here." },
];

export function RightRail() {
  const [open, setOpen] = useState<string | null>(null);
  const card = CARDS.find((c) => c.id === open);
  return (
    <>
      <nav aria-label="Panels" className="flex w-12 shrink-0 flex-col items-center gap-1 border-l bg-card py-2 max-md:hidden">
        {CARDS.map((c) => (
          <Tip key={c.id} label={c.label} side="left">
            <button type="button" aria-label={c.label} aria-expanded={open === c.id} aria-controls={`card-${c.id}`}
              onClick={() => setOpen((o) => (o === c.id ? null : c.id))}
              className={cn("grid size-9 place-items-center rounded-lg text-muted-foreground outline-none transition-colors hover:bg-muted hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 aria-expanded:bg-muted aria-expanded:text-foreground")}>
              <c.icon className="size-4" />
            </button>
          </Tip>
        ))}
      </nav>
      {card && (
        <FloatingCard id={`card-${card.id}`} title={card.label} onClose={() => setOpen(null)}>
          <EmptyState>{card.empty}</EmptyState>
        </FloatingCard>
      )}
    </>
  );
}
