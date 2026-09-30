"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import type { Data, Layout } from "plotly.js";

const Plot = dynamic(
  async () => {
    const Plotly = (await import("plotly.js-basic-dist-min")).default;
    const factory = (await import("react-plotly.js/factory")).default;
    return factory(Plotly);
  },
  {
    ssr: false,
    loading: () => <div className="h-full w-full animate-pulse rounded-md bg-muted" />,
  },
);

function useDark() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const el = document.documentElement;
    const read = () => setDark(el.classList.contains("dark"));
    read();
    const mo = new MutationObserver(read);
    mo.observe(el, { attributes: true, attributeFilter: ["class"] });
    return () => mo.disconnect();
  }, []);
  return dark;
}

export function usePlotTheme() {
  const dark = useDark();
  return dark
    ? { fg: "#e5e5e5", grid: "#2e2e2e", muted: "#a3a3a3", series: ["#60a5fa", "#fbbf24", "#f87171", "#34d399"] }
    : { fg: "#262626", grid: "#e5e5e5", muted: "#737373", series: ["#2563eb", "#d97706", "#dc2626", "#059669"] };
}

type Props = {
  data: Partial<Data>[];
  layout: Partial<Layout>;
  onPointClick?: (customdata: unknown) => void;
};

export function BasePlot({ data, layout, onPointClick }: Props) {
  const t = usePlotTheme();
  const axis = {
    gridcolor: t.grid, zerolinecolor: t.grid, linecolor: t.muted,
    tickfont: { color: t.muted, size: 11 }, ticks: "outside" as const, tickcolor: t.muted,
  };
  const merged: Partial<Layout> = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "var(--font-geist-mono), ui-monospace, monospace", color: t.fg, size: 12 },
    margin: { l: 64, r: 16, t: 16, b: 84 },
    legend: { orientation: "h", y: -0.32, font: { color: t.fg } },
    hoverlabel: { font: { family: "var(--font-geist-mono), monospace" } },
    ...layout,
    xaxis: { ...axis, ...layout.xaxis, title: { text: layout.xaxis?.title as string, font: { color: t.fg } } },
    yaxis: { ...axis, ...layout.yaxis, title: { text: layout.yaxis?.title as string, font: { color: t.fg } } },
  };
  return (
    <Plot
      data={data}
      layout={merged}
      config={{ displaylogo: false, responsive: true }}
      useResizeHandler
      style={{ width: "100%", height: "100%" }}
      onClick={(e) => onPointClick?.(e.points[0]?.customdata)}
    />
  );
}
