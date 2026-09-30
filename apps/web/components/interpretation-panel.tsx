"use client";

import { Wand2 } from "lucide-react";
import type { InversionResult, LayerInterp, Lithology, Suggestion } from "@/lib/api";
import { API_URL } from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Pick } from "./pick";

export const BLANK: LayerInterp = { lithology: "unclassified", confidence: "low", basis: "", notes: "" };

export function InterpretationPanel({
  run, lithologies, confidenceLevels, interp, suggestions, columnUrl, columnError,
  context, conclusion, onInterp, onContext, onConclusion, onDraft,
}: {
  run: InversionResult;
  lithologies: Lithology[];
  confidenceLevels: string[];
  interp: LayerInterp[];
  suggestions: Suggestion[][];
  columnUrl: string | null;
  columnError: string | null;
  context: string;
  conclusion: string;
  onInterp: (i: number, patch: Partial<LayerInterp>) => void;
  onContext: (v: string) => void;
  onConclusion: (v: string) => void;
  onDraft: () => void;
}) {
  const byId = Object.fromEntries(lithologies.map((l) => [l.id, l]));
  const used = Array.from(new Set(interp.map((l) => l.lithology)));
  return (
    <div className="grid gap-4">
      <Alert>
        <AlertTitle>Interpretation is yours, not the software&apos;s</AlertTitle>
        <AlertDescription>
          Suggestions come from broad, overlapping resistivity ranges and do not identify lithology.
          Saturation, pore-water salinity, clay content and geology all shift resistivity. Choose a lithology only
          where you have a basis, and state your confidence.
        </AlertDescription>
      </Alert>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,420px)_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Geological column</CardTitle>
            <CardDescription>Colours and patterns follow lithologic-column conventions.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            {columnError && <p className="text-sm text-destructive">{columnError}</p>}
            {columnUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={columnUrl} alt="Interpreted geological column" className="w-full rounded-md border bg-white" />
            ) : (
              <div className="h-64 animate-pulse rounded-md bg-muted" />
            )}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`${API_URL}/figures/legend?ids=${used.join(",")}`}
              alt="Lithology legend" className="w-44 rounded-md border bg-white"
            />
          </CardContent>
        </Card>

        <div className="grid content-start gap-4">
          {run.resistivity.map((rho, i) => {
            const it = interp[i] ?? BLANK;
            const lit = byId[it.lithology];
            const sug = suggestions[i] ?? [];
            return (
              <Card key={i}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <span className="inline-block size-3 rounded-sm border" style={{ background: lit?.color ?? "#fff" }} />
                    Layer {i + 1}
                    <span className="font-normal text-muted-foreground">
                      ρ {Number(rho.toPrecision(3))} Ωm · {run.depth_top[i].toFixed(2)}–{run.depth_bottom[i] == null ? "∞" : run.depth_bottom[i]!.toFixed(2)} m
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="grid gap-3">
                  {sug.length > 0 && (
                    <div className="grid gap-1.5">
                      <Label className="text-xs text-muted-foreground">Possible (ranked, not a verdict)</Label>
                      <div className="flex flex-wrap gap-1.5">
                        {sug.map((s) => (
                          <Button key={s.id} size="xs" variant={it.lithology === s.id ? "default" : "outline"}
                            title={s.basis}
                            onClick={() => onInterp(i, { lithology: s.id, basis: it.basis || s.basis })}>
                            {s.name}{s.in_range ? "" : " (outside range)"}
                          </Button>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="grid gap-2">
                      <Label>Lithology</Label>
                      <Pick label={`Layer ${i + 1} lithology`} value={it.lithology} onChange={(v) => onInterp(i, { lithology: v })}
                        options={lithologies.map((l) => ({ value: l.id, label: l.name }))} />
                    </div>
                    <div className="grid gap-2">
                      <Label>Confidence</Label>
                      <Pick label={`Layer ${i + 1} confidence`} value={it.confidence} onChange={(v) => onInterp(i, { confidence: v })}
                        options={confidenceLevels.map((c) => ({ value: c, label: c }))} />
                    </div>
                  </div>
                  <div className="grid gap-2">
                    <div className="flex items-center justify-between">
                      <Label>Basis</Label>
                      {sug[0] && (
                        <Button size="xs" variant="ghost" onClick={() => onInterp(i, { basis: (sug.find((s) => s.id === it.lithology) ?? sug[0]).basis })}>
                          <Wand2 /> Use suggested wording
                        </Button>
                      )}
                    </div>
                    <Textarea aria-label={`Layer ${i + 1} basis`} rows={2} value={it.basis} placeholder="Why this lithology? Resistivity range, depth, borehole, local geology…"
                      onChange={(e) => onInterp(i, { basis: e.target.value })} />
                  </div>
                  <div className="grid gap-2">
                    <Label>Notes</Label>
                    <Textarea aria-label={`Layer ${i + 1} notes`} rows={1} value={it.notes} onChange={(e) => onInterp(i, { notes: e.target.value })} />
                  </div>
                  {lit && lit.id !== "unclassified" && (
                    <p className="text-xs text-muted-foreground">
                      Indicative range for {lit.name.toLowerCase()}: {lit.rho_min}–{lit.rho_max} Ωm <Badge variant="outline">unverified</Badge>
                    </p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Geological context</CardTitle>
            <CardDescription>Local geology, boreholes, water conditions, known resistivity ranges.</CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea aria-label="Geological context" rows={5} value={context} onChange={(e) => onContext(e.target.value)} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Conclusion</CardTitle>
            <CardDescription>Leave empty to use an automatically drafted summary in the report.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2">
            <Textarea aria-label="Conclusion" rows={5} value={conclusion} onChange={(e) => onConclusion(e.target.value)} />
            <Button size="sm" variant="outline" className="w-fit" onClick={onDraft}><Wand2 /> Draft from results</Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
