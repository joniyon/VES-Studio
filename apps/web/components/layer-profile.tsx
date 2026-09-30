"use client";

import type { InversionResult } from "@/lib/api";
import { BasePlot, usePlotTheme } from "./plot";

/** Stepped resistivity-depth profile of the 1D layer model. */
export function LayerProfile({ result }: { result: InversionResult }) {
  const t = usePlotTheme();
  const n = result.resistivity.length;
  const last = result.depth_top[n - 1];
  const bottom = Math.max(last * 1.6, last + 5);
  const x: number[] = [];
  const y: number[] = [];
  result.resistivity.forEach((rho, i) => {
    const top = result.depth_top[i];
    const bot = result.depth_bottom[i] ?? bottom;
    x.push(rho, rho);
    y.push(top, bot);
  });
  return (
    <BasePlot
      data={[{
        x, y, type: "scatter", mode: "lines", line: { color: t.series[0], width: 2.5, shape: "hv" },
        hovertemplate: "ρ %{x:.4g} Ωm<br>depth %{y:.3g} m<extra></extra>", name: "layer model",
      }]}
      layout={{
        showlegend: false,
        xaxis: { type: "log", title: "Resistivity (Ωm)" } as never,
        yaxis: { autorange: "reversed", title: "Depth (m)" } as never,
      }}
    />
  );
}
