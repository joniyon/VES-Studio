export type StepId = "project" | "data" | "qc" | "curve" | "inversion" | "interpretation" | "export";

export const STEPS: { id: StepId; n: number; label: string }[] = [
  { id: "project", n: 0, label: "Project" },
  { id: "data", n: 1, label: "Data" },
  { id: "qc", n: 2, label: "QC" },
  { id: "curve", n: 3, label: "Curve" },
  { id: "inversion", n: 4, label: "Inversion" },
  { id: "interpretation", n: 5, label: "Interpretation" },
  { id: "export", n: 6, label: "Report" },
];

export type StepFlags = { processed: boolean; hasRun: boolean };

/** Why a step is locked, or null when it is available. Same rules the tabs have always had. */
export function lockHint(id: StepId, f: StepFlags): string | null {
  if (id === "interpretation") return f.hasRun ? null : "Needs an inversion run: run the inversion in 4 · Inversion.";
  if (id === "project" || id === "data") return null;
  return f.processed ? null : "Needs processed data: load a file and press Process in 1 · Data.";
}

export type DoneInput = {
  projectNamed: boolean; processed: boolean; hasRun: boolean;
  visited: ReadonlySet<StepId>; interpreted: boolean; exported: boolean;
};

/** Completed-step check marks, derived from existing state only. */
export function isDone(id: StepId, d: DoneInput): boolean {
  switch (id) {
    case "project": return d.projectNamed;
    case "data": return d.processed;
    case "qc": return d.processed && d.visited.has("qc");
    case "curve": return d.processed && d.visited.has("curve");
    case "inversion": return d.hasRun;
    case "interpretation": return d.hasRun && d.interpreted;
    case "export": return d.exported;
  }
}
