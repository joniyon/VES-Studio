"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { AlertTriangle, Info, X, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type ToastKind = "info" | "warning" | "error";
export type ToastInput = {
  kind?: ToastKind;
  text: string;
  action?: { label: string; onClick: () => void };
  /** milliseconds; default 5000 */
  duration?: number;
};
type ToastItem = ToastInput & { id: number; kind: ToastKind };

const MAX_VISIBLE = 3;
const ToastContext = createContext<(t: ToastInput) => void>(() => {});

/** `const toast = useToast(); toast({ kind: "info", text: "…" })` */
export const useToast = () => useContext(ToastContext);

const STYLE: Record<ToastKind, { icon: typeof Info; bar: string; tone: string }> = {
  info: { icon: Info, bar: "border-l-info", tone: "text-info" },
  warning: { icon: AlertTriangle, bar: "border-l-warning", tone: "text-warning" },
  error: { icon: XCircle, bar: "border-l-destructive", tone: "text-destructive" },
};

function Toast({ item, onDismiss }: { item: ToastItem; onDismiss: (id: number) => void }) {
  const [paused, setPaused] = useState(false);
  const { icon: Icon, bar, tone } = STYLE[item.kind];
  useEffect(() => {
    if (paused) return;
    const t = setTimeout(() => onDismiss(item.id), item.duration ?? 5000);
    return () => clearTimeout(t);
  }, [paused, item.id, item.duration, onDismiss]);
  return (
    <div
      role={item.kind === "error" ? "alert" : "status"}
      onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}
      className={cn(
        "pointer-events-auto flex items-start gap-2.5 rounded-xl border border-l-4 bg-popover px-3 py-2.5 text-sm text-popover-foreground shadow-[var(--shadow-float)]",
        "animate-in fade-in-0 slide-in-from-bottom-2 duration-150", bar,
      )}
    >
      <Icon className={cn("mt-0.5 size-4 shrink-0", tone)} aria-hidden />
      <p className="min-w-0 flex-1 break-words">{item.text}</p>
      {item.action && (
        <Button size="xs" variant="outline" onClick={() => { item.action?.onClick(); onDismiss(item.id); }}>{item.action.label}</Button>
      )}
      <Button size="icon-xs" variant="ghost" aria-label="Dismiss notification" onClick={() => onDismiss(item.id)}><X /></Button>
    </div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const dismiss = useCallback((id: number) => setItems((l) => l.filter((t) => t.id !== id)), []);
  const push = useCallback((t: ToastInput) => {
    setItems((l) => [...l, { ...t, kind: t.kind ?? "info", id: Date.now() + Math.random() }].slice(-MAX_VISIBLE));
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4">
        <div className="flex w-full max-w-md flex-col gap-2">
          {items.map((t) => <Toast key={t.id} item={t} onDismiss={dismiss} />)}
        </div>
      </div>
    </ToastContext.Provider>
  );
}
