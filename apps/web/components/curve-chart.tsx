"use client";

import type { InversionResult, ProcessedRow } from "@/lib/api";
import { BasePlot, usePlotTheme } from "./plot";

/** Column holding the plotted spacing (metres) for each array. */
export function spacingKey(rows: ProcessedRow[]): string | null {
  const k = ["ab_half_m", "a_m", "x_m", "ab_m"].find((c) => rows[0] && c in rows[0]);
  return k ?? null;
}

export function CurveChart({
  rows, model, selected, onSelect,
}: {
  rows: ProcessedRow[];
  model: InversionResult | null;
  selected: number | null;
  onSelect: (sourceRow: number) => void;
}) {
  const t = usePlotTheme();
  const key = spacingKey(rows);
  if (!key) return null;
  const valid = rows.filter((r) => r.apparent_resistivity != null && (r.apparent_resistivity as number) > 0);
  const pick = (status: string[]) => valid.filter((r) => status.includes(r.qc_status));
  const trace = (rs: ProcessedRow[], name: string, color: string, symbol: "circle" | "diamond") => ({
    x: rs.map((r) => r[key] as number),
    y: rs.map((r) => r.apparent_resistivity as number),
    customdata: rs.map((r) => r.source_row) as unknown as never,
    name, type: "scatter" as const, mode: "markers" as const,
    marker: { color, symbol, size: rs.map((r) => (r.source_row === selected ? 13 : 8)) },
    hovertemplate: "row %{customdata}<br>spacing %{x:.4g} m<br>ρa %{y:.4g} Ωm<extra>" + name + "</extra>",
  });
  const data = [
    trace(pick(["PASS"]), "observed", t.series[0], "circle"),
    trace(pick(["WARNING"]), "observed (warning)", t.series[1], "diamond"),
    ...(model
      ? [{
          x: model.spacing, y: model.model_response, name: "model response",
          type: "scatter" as const, mode: "lines" as const,
          line: { color: t.series[3], width: 2 }, hovertemplate: "model ρa %{y:.4g} Ωm<extra></extra>",
        }]
      : []),
  ].filter((d) => d.x.length > 0);
  return (
    <BasePlot
      data={data}
      layout={{
        xaxis: { type: "log", title: "Electrode spacing (m)" } as never,
        yaxis: { type: "log", title: "Apparent resistivity (Ωm)" } as never,
      }}
      onPointClick={(c) => typeof c === "number" && onSelect(c)}
    />
  );
}
