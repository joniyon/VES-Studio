"use client";

import { FileDown, FileText, Image as ImageIcon, Table2, Braces } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export type ExportAction = { key: string; label: string; hint: string; needsRun: boolean; run: () => void };

const ICONS: Record<string, React.ReactNode> = {
  pdf: <FileText />, csv: <Table2 />, img: <ImageIcon />, json: <Braces />,
};

export function ExportPanel({
  actions, hasRun, busy, message,
}: { actions: ExportAction[]; hasRun: boolean; busy: string | null; message: string | null }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Report & export</CardTitle>
        <CardDescription>
          Everything is regenerated from your data and settings, so files always match what you see.
          {!hasRun && " Run an inversion to enable results exports."}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {actions.map((a) => (
          <Button key={a.key} variant={a.key === "pdf" ? "default" : "outline"} className="h-auto justify-start gap-3 py-3 text-left"
            disabled={(a.needsRun && !hasRun) || busy !== null} onClick={a.run}>
            {ICONS[a.key.split(":")[0]] ?? <FileDown />}
            <span className="grid">
              <span>{busy === a.key ? "Preparing…" : a.label}</span>
              <span className="text-xs font-normal opacity-70">{a.hint}</span>
            </span>
          </Button>
        ))}
        {message && <p className="col-span-full text-sm text-muted-foreground">{message}</p>}
      </CardContent>
    </Card>
  );
}
