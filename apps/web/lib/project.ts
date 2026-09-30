import type { InversionConfig, LayerInterp, Units } from "./api";
import type { Mapping, RawTable } from "./table";

export type ProjectMeta = {
  name: string; location: string; client: string; researcher: string;
  survey_date: string; status: string; description: string; notes: string;
};
export type StationMeta = {
  id: string; latitude: string; longitude: string; elevation: string;
  location_description: string; survey_date: string; notes: string;
};
export type UploadInfo = {
  file_name: string; sha256: string; sheet?: string; table: RawTable;
  /** original bytes kept for the record: text for CSV, base64 for XLSX */
  original: { kind: "text" | "base64"; data: string } | null;
};
export type HistoryEvent = { t: string; text: string };

export type SavedState = {
  format: "ves-studio-project";
  version: 1;
  saved_at: string;
  project: ProjectMeta;
  station: StationMeta;
  upload: UploadInfo | null;
  arrayId: string;
  units: Units;
  useVI: boolean;
  mapping: Mapping;
  excluded: number[];
  runs: { config: InversionConfig; excluded: number[] }[];
  activeRun: number | null;
  interpretation: Record<string, LayerInterp[]>;   // keyed by run_id
  geologicalContext: string;
  conclusion: string;
  history: HistoryEvent[];
};

export const EMPTY_PROJECT: ProjectMeta = {
  name: "", location: "", client: "", researcher: "", survey_date: "", status: "Draft", description: "", notes: "",
};
export const EMPTY_STATION: StationMeta = {
  id: "VES-001", latitude: "", longitude: "", elevation: "", location_description: "", survey_date: "", notes: "",
};

const KEY = "ves-studio-project-v1";

export function loadSaved(): SavedState | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const s = JSON.parse(raw);
    return s?.format === "ves-studio-project" && s.version === 1 ? (s as SavedState) : null;
  } catch { return null; }
}

export function save(s: SavedState) {
  try { localStorage.setItem(KEY, JSON.stringify(s)); } catch { /* quota or disabled: non-fatal */ }
}

export function clearSaved() {
  try { localStorage.removeItem(KEY); } catch {}
}

export function parseProjectFile(text: string): SavedState {
  let s: SavedState;
  try { s = JSON.parse(text); } catch { throw new Error("That file is not valid JSON."); }
  if (s?.format !== "ves-studio-project") throw new Error("Not a VES Studio project file.");
  if (s.version !== 1) throw new Error(`Unsupported project file version ${String(s.version)}.`);
  return s;
}

export async function sha256Hex(data: ArrayBuffer | string): Promise<string> {
  const buf = typeof data === "string" ? new TextEncoder().encode(data) : new Uint8Array(data);
  const d = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(d)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function toBase64(buf: ArrayBuffer): string {
  let bin = "";
  const b = new Uint8Array(buf);
  for (let i = 0; i < b.length; i += 0x8000) bin += String.fromCharCode(...b.subarray(i, i + 0x8000));
  return btoa(bin);
}

export function validateStation(st: StationMeta): Record<string, string> {
  const e: Record<string, string> = {};
  const num = (v: string) => v.trim() !== "" && Number.isFinite(Number(v));
  if (st.latitude.trim() && (!num(st.latitude) || Math.abs(Number(st.latitude)) > 90)) e.latitude = "Latitude must be between −90 and 90.";
  if (st.longitude.trim() && (!num(st.longitude) || Math.abs(Number(st.longitude)) > 180)) e.longitude = "Longitude must be between −180 and 180.";
  if (st.elevation.trim() && !num(st.elevation)) e.elevation = "Elevation must be a number (m).";
  if (!st.id.trim()) e.id = "Station ID is required.";
  return e;
}

export function download(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const slug = (s: string) => s.trim().replace(/[^a-zA-Z0-9_-]+/g, "_").replace(/^_+|_+$/g, "") || "ves";
