export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Severity = "INFO" | "WARNING" | "ERROR";
export type Issue = {
  severity: Severity;
  code: string;
  message: string;
  row: number | null;
  field: string | null;
};
export type ArrayField = { name: string; label: string; kind: "distance" | "integer" };
export type ArrayMeta = { id: string; title: string; fields: ArrayField[]; references: string[] };
export type ArraysResponse = { arrays: ArrayMeta[]; units: Record<string, string[]> };
export type Units = { distance: string; resistance: string; voltage: string; current: string; resistivity: string };

export type ProcessedRow = Record<string, number | string | null> & {
  source_row: number;
  geometric_factor: number | null;
  apparent_resistivity: number | null;
  resistance_ohm: number | null;
  qc_status: "PASS" | "WARNING" | "ERROR" | "EXCLUDED";
};
export type ProcessResponse = {
  rows: ProcessedRow[];
  issues: Issue[];
  has_errors: boolean;
  lineage: Record<string, unknown>;
  error?: string;
};

export type Lithology = {
  id: string; name: string; group: string; color: string; hatch: string;
  rho_min: number; rho_max: number; verified: boolean;
};
export type LithologyResponse = { lithologies: Lithology[]; confidence_levels: string[]; note: string };
export type Suggestion = { id: string; name: string; in_range: boolean; depth_ok: boolean; score: number; basis: string };
export type LayerInterp = { lithology: string; confidence: string; basis: string; notes: string };

export type InversionConfig = { n_layers: number; error_percent: number; lam?: number; max_iter?: number };
export type InversionResult = {
  run_id: string;
  config: InversionConfig;
  resistivity: number[];
  thickness: number[];
  depth_top: number[];
  depth_bottom: (number | null)[];
  spacing: number[];
  observed: number[];
  model_response: number[];
  rms_percent: number;
  chi2: number;
  iterations: number;
  converged: boolean;
  metadata: Record<string, unknown>;
  warnings: string[];
  error?: string;
};

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    throw new Error(
      `Cannot reach the geophysics API at ${API_URL}. Start it with: uvicorn app.api.main:app --port 8000`,
    );
  }
  const body = await res.json();
  if (!res.ok || body.error) throw new Error(body.error ?? `Request failed (${res.status})`);
  return body as T;
}

const post = (path: string, payload: unknown) =>
  call<never>(path, { method: "POST", body: JSON.stringify(payload) });

export const getArrays = () => call<ArraysResponse>("/arrays");
export const getLithologies = () => call<LithologyResponse>("/lithologies");
export const suggestLithology = (layers: { resistivity: number; depth_top: number; depth_bottom: number | null }[]) =>
  post("/suggest-lithology", { layers }) as Promise<{ layers: Suggestion[][] }>;

export async function parseXlsx(file: File, sheet?: string) {
  const fd = new FormData();
  fd.append("file", file);
  if (sheet) fd.append("sheet", sheet);
  let res: Response;
  try { res = await fetch(`${API_URL}/parse-xlsx`, { method: "POST", body: fd }); }
  catch { throw new Error(`Cannot reach the geophysics API at ${API_URL}.`); }
  const body = await res.json();
  if (!res.ok) throw new Error(body.error ?? "Could not read the workbook.");
  return body as { sheets: string[]; sheet: string; headers: string[]; rows: string[][] };
}

/** POST JSON and return the response as a Blob (figures, CSV, PDF). */
export async function fetchBlob(path: string, payload?: unknown): Promise<Blob> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, payload === undefined ? {} : {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
  } catch { throw new Error(`Cannot reach the geophysics API at ${API_URL}.`); }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try { msg = (await res.json()).error ?? msg; } catch {}
    throw new Error(msg);
  }
  return res.blob();
}
export type Payload = {
  array: string; units: Units; rows: Record<string, unknown>[]; excluded_rows: number[]; assume_point_mn: boolean;
};
export const processData = (p: Payload) =>
  post("/process", p) as Promise<ProcessResponse>;
export const invert = (p: Payload & { config: InversionConfig }) =>
  post("/invert", p) as Promise<InversionResult>;
