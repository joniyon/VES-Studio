"use client";

import { Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tip } from "@/components/ui/tooltip";
import { useToast } from "./ToastHost";

export type StatusInfo = {
  api: "connected" | "unavailable" | "checking";
  engine?: string;
  array?: string;
  station?: string;
  points?: string;
  run?: string;
};

/** Bottom-left monospace status; the copy button puts the same text on the clipboard. */
export function StatusPanel({ info }: { info: StatusInfo }) {
  const toast = useToast();
  const rows: [string, string][] = [
    ["api", info.api === "connected" ? `connected${info.engine ? ` · engine v${info.engine}` : ""}` : info.api],
    ["array", info.array ?? "—"],
    ["station", info.station || "—"],
    ["points", info.points ?? "—"],
    ["run", info.run ?? "—"],
  ];
  const text = rows.map(([k, v]) => `${k.padEnd(8)}${v}`).join("\n");
  const copy = async () => {
    try { await navigator.clipboard.writeText(text); toast({ text: "Status copied to the clipboard." }); }
    catch { toast({ kind: "warning", text: "Could not copy: clipboard access was blocked." }); }
  };
  return (
    <section aria-label="Status" className="absolute bottom-3 left-14 z-20 rounded-xl border bg-popover/95 px-3 py-2 font-mono text-[11px] leading-5 text-popover-foreground shadow-[var(--shadow-float)] backdrop-blur max-md:hidden">
      <div className="flex items-start gap-3">
        <dl className="grid grid-cols-[auto_1fr] gap-x-3">
          {rows.map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-muted-foreground">{k}</dt>
              <dd className="max-w-64 truncate" title={v}>{k === "api" ? <><span className={info.api === "connected" ? "text-success" : info.api === "unavailable" ? "text-destructive" : "text-muted-foreground"}>●</span> {v}</> : v}</dd>
            </div>
          ))}
        </dl>
        <Tip label="Copy status" side="top">
          <Button size="icon-xs" variant="ghost" aria-label="Copy status" onClick={copy}><Copy /></Button>
        </Tip>
      </div>
    </section>
  );
}
