import type { ArrayMeta } from "./api";

export type RawTable = { headers: string[]; rows: string[][] };

/** Minimal CSV parser with quoted-field support. */
export function parseCsv(text: string): RawTable {
  const rows: string[][] = [];
  let cur: string[] = [];
  let field = "";
  let quoted = false;
  const src = text.replace(/\r\n?/g, "\n");
  for (let i = 0; i < src.length; i++) {
    const ch = src[i];
    if (quoted) {
      if (ch === '"' && src[i + 1] === '"') { field += '"'; i++; }
      else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { cur.push(field); field = ""; }
    else if (ch === "\n") { cur.push(field); rows.push(cur); cur = []; field = ""; }
    else field += ch;
  }
  if (field !== "" || cur.length) { cur.push(field); rows.push(cur); }
  const nonEmpty = rows.filter((r) => r.some((c) => c.trim() !== ""));
  const [headers = [], ...body] = nonEmpty;
  return { headers: headers.map((h) => h.trim()), rows: body };
}

const ALIASES: Record<string, string[]> = {
  ab_half: ["ab2", "abhalf", "halfab"],
  mn_half: ["mn2", "mnhalf", "halfmn"],
  a: ["a", "spacing", "electrodespacing"],
  n: ["n", "nfactor", "level"],
  ab: ["ab", "abspacing"],
  mn: ["mn", "mnspacing"],
  x: ["x", "offset", "position"],
  resistance: ["r", "res", "resistance", "rohm", "rohms"],
  apparent_resistivity: ["rhoa", "rho", "apparentresistivity", "resistivity", "ohmm", "pa"],
  voltage: ["v", "voltage", "dv", "deltav", "vmn"],
  current: ["i", "current", "amps", "iab"],
};
const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, "");

export type Mapping = Record<string, number>; // canonical field -> header index (-1 = unmapped)

export type Measurement = "r" | "vi" | "rho";

export function targetFields(arr: ArrayMeta, mode: Measurement, assumeMn = false): string[] {
  const geometry = arr.fields.map((f) => f.name).filter((f) => !(assumeMn && f === "mn_half"));
  return [...geometry, ...(mode === "vi" ? ["voltage", "current"] : mode === "rho" ? ["apparent_resistivity"] : ["resistance"])];
}

export function autoMap(headers: string[], fields: string[]): Mapping {
  const used = new Set<number>();
  const m: Mapping = {};
  for (const f of fields) {
    const names = [f, ...(ALIASES[f] ?? [])].map(norm);
    const idx = headers.findIndex((h, i) => !used.has(i) && names.includes(norm(h)));
    m[f] = idx;
    if (idx >= 0) used.add(idx);
  }
  return m;
}

/** Build engine input rows. Non-numeric cells are passed through so the engine flags them. */
export function buildRows(t: RawTable, m: Mapping, fields: string[]): Record<string, unknown>[] {
  return t.rows.map((r) => {
    const o: Record<string, unknown> = {};
    for (const f of fields) {
      const i = m[f];
      const raw = i >= 0 ? (r[i] ?? "").trim() : "";
      o[f] = raw === "" ? null : Number.isFinite(Number(raw)) ? Number(raw) : raw;
    }
    return o;
  });
}
