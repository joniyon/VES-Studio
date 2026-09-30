"use client";

import { Info } from "lucide-react";
import { NO_WORKING, type WorkingConfig, type WorkingPreview } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Pick } from "./pick";

const PRESETS: { id: string; label: string; hint: string; cfg: WorkingConfig }[] = [
  { id: "raw", label: "Raw data", hint: "Fit exactly what was measured", cfg: NO_WORKING },
  { id: "hanning", label: "Average + Hanning", hint: "Smooth scatter (closest to WinResist on Ayetoro VES 2)", cfg: { overlap: "average", anchor_segment: 0, smooth: "hanning", window: 3 } },
  { id: "median", label: "Average + median", hint: "Robust to a few bad readings", cfg: { overlap: "average", anchor_segment: 0, smooth: "median", window: 3 } },
];
const same = (a: WorkingConfig, b: WorkingConfig) =>
  a.overlap === b.overlap && a.smooth === b.smooth && (a.smooth === "none" || a.window === b.window) &&
  (a.overlap !== "shift" || a.anchor_segment === b.anchor_segment);

export function WorkingCurveCard({
  value, onChange, preview, available,
}: { value: WorkingConfig; onChange: (w: WorkingConfig) => void; preview: WorkingPreview | null; available: boolean }) {
  if (!available) {
    return (
      <Card>
        <CardHeader><CardTitle>Data preparation</CardTitle></CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Shifting, averaging and smoothing are available for Schlumberger, Wenner and pole-pole soundings only.
        </CardContent>
      </Card>
    );
  }
  const maxSeg = preview?.n_segments ?? 1;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Data preparation</CardTitle>
        <CardDescription>
          Your raw readings are never changed. Preparation builds a working curve that the inversion fits; misfit is
          reported against both. Noisy field data often look like a textbook VES curve only after this step.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <Button key={p.id} size="sm" variant={same(value, p.cfg) ? "default" : "outline"} title={p.hint} onClick={() => onChange(p.cfg)}>
              {p.label}
            </Button>
          ))}
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="grid gap-2">
            <Label>Repeated spacings (MN change)</Label>
            <Pick label="Overlap handling" value={value.overlap} onChange={(v) => onChange({ ...value, overlap: v as WorkingConfig["overlap"] })}
              options={[{ value: "none", label: "Keep all points" }, { value: "average", label: "Average" }, { value: "shift", label: "Shift segments, then average" }]} />
          </div>
          {value.overlap === "shift" && (
            <div className="grid gap-2">
              <Label>Anchor segment</Label>
              <Pick label="Anchor segment" value={String(Math.min(value.anchor_segment, maxSeg - 1))} onChange={(v) => onChange({ ...value, anchor_segment: Number(v) })}
                options={Array.from({ length: maxSeg }, (_, i) => ({ value: String(i), label: `Segment ${i + 1}` }))} />
            </div>
          )}
          <div className="grid gap-2">
            <Label>Smoothing</Label>
            <Pick label="Smoothing" value={value.smooth} onChange={(v) => onChange({ ...value, smooth: v as WorkingConfig["smooth"] })}
              options={[{ value: "none", label: "None" }, { value: "hanning", label: "Hanning (weighted mean)" }, { value: "median", label: "Median" }]} />
          </div>
          {value.smooth !== "none" && (
            <div className="grid gap-2">
              <Label>Window</Label>
              <Pick label="Smoothing window" value={String(value.window)} onChange={(v) => onChange({ ...value, window: Number(v) as 3 | 5 })}
                options={[{ value: "3", label: "3 points" }, { value: "5", label: "5 points" }]} />
            </div>
          )}
        </div>
        {value.overlap === "shift" && (
          <p className="flex gap-2 text-xs text-amber-600 dark:text-amber-400">
            <Info className="mt-0.5 size-3.5 shrink-0" />
            Shifting trusts every overlap pair. With noisy readings it can make the fit worse — use it only when the offsets look systematic.
          </p>
        )}
        {preview && !preview.error && !preview.identity && (
          <div className="grid gap-1 text-xs text-muted-foreground">
            <p>Working curve: {preview.spacing.length} points. {preview.description}.</p>
            {value.overlap === "shift" && (
              <p>Segment factors: {preview.shifts.map((s, i) => `${i + 1}: ×${s.toFixed(2)}`).join(" · ")}</p>
            )}
            {preview.notes.map((n, i) => <p key={i}>{n}</p>)}
          </div>
        )}
        {preview?.error && <p className="text-sm text-destructive">{preview.error}</p>}
      </CardContent>
    </Card>
  );
}
