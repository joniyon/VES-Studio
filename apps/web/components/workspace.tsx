"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, FlaskConical, Info, Loader2, Upload, XCircle } from "lucide-react";
import {
  getArrays, invert, processData,
  type ArrayMeta, type ArraysResponse, type InversionResult, type Issue,
  type ProcessResponse, type ProcessedRow, type Units,
} from "@/lib/api";
import { SAMPLE_CSV } from "@/lib/sample";
import { autoMap, buildRows, parseCsv, targetFields, type Mapping, type RawTable } from "@/lib/table";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CurveChart } from "./curve-chart";
import { LayerProfile } from "./layer-profile";
import { Pick } from "./pick";
import { ThemeToggle } from "./theme-toggle";

const fmt = (v: unknown, d = 4) =>
  typeof v === "number" ? (Math.abs(v) >= 1e4 || (v !== 0 && Math.abs(v) < 1e-2) ? v.toExponential(3) : Number(v.toPrecision(d)).toString()) : "—";

const DEFAULT_UNITS: Units = { distance: "m", resistance: "ohm", voltage: "V", current: "A" };
const UNSET = "-1";

function SeverityIcon({ s }: { s: Issue["severity"] }) {
  if (s === "ERROR") return <XCircle className="size-4 shrink-0 text-destructive" />;
  if (s === "WARNING") return <AlertTriangle className="size-4 shrink-0 text-amber-500" />;
  return <Info className="size-4 shrink-0 text-muted-foreground" />;
}

function StatusBadge({ s }: { s: string }) {
  return (
    <Badge variant={s === "ERROR" ? "destructive" : s === "WARNING" ? "secondary" : "outline"}>{s}</Badge>
  );
}

export function Workspace() {
  const [meta, setMeta] = useState<ArraysResponse | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [arrayId, setArrayId] = useState("schlumberger");
  const [units, setUnits] = useState<Units>(DEFAULT_UNITS);
  const [useVI, setUseVI] = useState(false);
  const [table, setTable] = useState<RawTable | null>(null);
  const [fileName, setFileName] = useState("");
  const [mapping, setMapping] = useState<Mapping>({});
  const [processed, setProcessed] = useState<ProcessResponse | null>(null);
  const [runs, setRuns] = useState<InversionResult[]>([]);
  const [activeRun, setActiveRun] = useState<number | null>(null);
  const [nLayers, setNLayers] = useState("3");
  const [errPct, setErrPct] = useState("3");
  const [selected, setSelected] = useState<number | null>(null);
  const [busy, setBusy] = useState<"process" | "invert" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [tab, setTab] = useState("data");

  useEffect(() => {
    getArrays().then(setMeta).catch((e: Error) => setApiError(e.message));
  }, []);

  const arr: ArrayMeta | undefined = meta?.arrays.find((a) => a.id === arrayId);
  const fields = useMemo(() => (arr ? targetFields(arr, useVI) : []), [arr, useVI]);

  const loadTable = (t: RawTable, name: string) => {
    setTable(t);
    setFileName(name);
    setProcessed(null);
    setRuns([]);
    setActiveRun(null);
    setSelected(null);
    setError(null);
    setNotice(null);
    if (arr) setMapping(autoMap(t.headers, targetFields(arr, useVI)));
  };

  const remap = (nextArr: ArrayMeta | undefined, vi: boolean) => {
    if (table && nextArr) setMapping(autoMap(table.headers, targetFields(nextArr, vi)));
    setProcessed(null);
    setRuns([]);
    setActiveRun(null);
  };

  const onFile = async (f: File | undefined) => {
    if (!f) return;
    if (!/\.csv$|\.txt$/i.test(f.name)) {
      setError("Only CSV is supported in this build. XLSX upload is planned.");
      return;
    }
    loadTable(parseCsv(await f.text()), f.name);
  };

  const missing = fields.filter((f) => (mapping[f] ?? -1) < 0);
  const payloadRows = () => (table ? buildRows(table, mapping, fields) : []);

  const runProcess = async () => {
    setBusy("process"); setError(null);
    try {
      const res = await processData({ array: arrayId, units, rows: payloadRows() });
      setProcessed(res);
      setRuns([]); setActiveRun(null);
      setTab("qc");
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(null); }
  };

  const runInvert = async () => {
    setBusy("invert"); setError(null);
    try {
      const res = await invert({
        array: arrayId, units, rows: payloadRows(),
        config: { n_layers: Number(nLayers), error_percent: Number(errPct) },
      });
      // Identical data + settings reproduce the identical run (same run_id): reuse it
      // instead of appending a duplicate. Any changed setting yields a new run.
      const existing = runs.findIndex((r) => r.run_id === res.run_id);
      if (existing >= 0) {
        setActiveRun(existing);
        setNotice(`Same data and settings as Run ${existing + 1} — the result is identical (reproducible).`);
      } else {
        setRuns([...runs, res]); // append-only history
        setActiveRun(runs.length);
        setNotice(null);
      }
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(null); }
  };

  const rows: ProcessedRow[] = processed?.rows ?? [];
  const run = activeRun != null ? runs[activeRun] : null;
  const sel = rows.find((r) => r.source_row === selected) ?? null;
  const issues = processed?.issues ?? [];
  const summary = issues.find((i) => i.code === "SUMMARY");
  const counts = {
    ERROR: issues.filter((i) => i.severity === "ERROR").length,
    WARNING: issues.filter((i) => i.severity === "WARNING").length,
  };

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-6">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">VES Studio</h1>
          <p className="text-sm text-muted-foreground">
            Upload → array → map → validate → curve → invert → layer model
          </p>
        </div>
        <div className="flex items-center gap-2">
          {meta && <Badge variant="outline">API connected</Badge>}
          <ThemeToggle />
        </div>
      </header>

      {apiError && (
        <Alert variant="destructive">
          <XCircle />
          <AlertTitle>Geophysics API unavailable</AlertTitle>
          <AlertDescription>{apiError}</AlertDescription>
        </Alert>
      )}
      {error && (
        <Alert variant="destructive">
          <XCircle />
          <AlertTitle>Something went wrong</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Tabs value={tab} onValueChange={(v) => setTab(String(v))}>
        <TabsList>
          <TabsTrigger value="data">1 · Data</TabsTrigger>
          <TabsTrigger value="qc" disabled={!processed}>2 · QC</TabsTrigger>
          <TabsTrigger value="curve" disabled={!processed}>3 · Curve</TabsTrigger>
          <TabsTrigger value="inversion" disabled={!processed}>4 · Inversion</TabsTrigger>
        </TabsList>

        {/* ---------------- 1 · DATA ---------------- */}
        <TabsContent value="data" className="mt-4 grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Array & units</CardTitle>
              <CardDescription>Units are never assumed silently — confirm them for your file.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              <div className="grid gap-2">
                <Label>Electrode array</Label>
                <Pick
                  value={arrayId}
                  onChange={(v) => { setArrayId(v); remap(meta?.arrays.find((a) => a.id === v), useVI); }}
                  options={(meta?.arrays ?? []).map((a) => ({ value: a.id, label: a.title }))}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                {(["distance", "resistance", "voltage", "current"] as const).map((q) => (
                  <div key={q} className="grid gap-2">
                    <Label className="capitalize">{q}</Label>
                    <Pick
                      value={units[q]}
                      onChange={(v) => setUnits((u) => ({ ...u, [q]: v }))}
                      options={(meta?.units[q] ?? []).map((u) => ({ value: u, label: u }))}
                    />
                  </div>
                ))}
              </div>
              <div className="grid gap-2">
                <Label>Measured quantity</Label>
                <Pick
                  value={useVI ? "vi" : "r"}
                  onChange={(v) => { setUseVI(v === "vi"); remap(arr, v === "vi"); }}
                  options={[{ value: "r", label: "Resistance" }, { value: "vi", label: "Voltage + current" }]}
                />
              </div>
              {arr && (
                <p className="text-xs text-muted-foreground">
                  References: {arr.references.join("; ")}
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Field data</CardTitle>
              <CardDescription>CSV upload, or load a synthetic 3-layer Schlumberger sounding.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3">
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" nativeButton={false} render={<label />}>
                  <Upload /> Choose CSV
                  <input type="file" accept=".csv,.txt" className="sr-only" onChange={(e) => onFile(e.target.files?.[0])} />
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setArrayId("schlumberger"); setUseVI(false); setUnits(DEFAULT_UNITS);
                    const sa = meta?.arrays.find((a) => a.id === "schlumberger");
                    const t = parseCsv(SAMPLE_CSV);
                    setTable(t); setFileName("synthetic_schlumberger_3layer.csv");
                    if (sa) setMapping(autoMap(t.headers, targetFields(sa, false)));
                    setProcessed(null); setRuns([]); setActiveRun(null); setSelected(null); setError(null);
                  }}
                >
                  <FlaskConical /> Load sample
                </Button>
              </div>
              {table ? (
                <>
                  <p className="text-sm">
                    <span className="font-medium">{fileName}</span>{" "}
                    <span className="text-muted-foreground">· {table.rows.length} rows · {table.headers.length} columns</span>
                  </p>
                  <ScrollArea className="h-44 rounded-md border">
                    <Table>
                      <TableHeader>
                        <TableRow>{table.headers.map((h) => <TableHead key={h}>{h}</TableHead>)}</TableRow>
                      </TableHeader>
                      <TableBody>
                        {table.rows.slice(0, 8).map((r, i) => (
                          <TableRow key={i}>{r.map((c, j) => <TableCell key={j} className="tabular-nums">{c}</TableCell>)}</TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">No file loaded.</p>
              )}
            </CardContent>
          </Card>

          {table && arr && (
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Column mapping</CardTitle>
                <CardDescription>
                  Detected automatically — check each field is pointing at the right column.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4">
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {fields.map((f) => {
                    const label = arr.fields.find((x) => x.name === f)?.label ?? f;
                    const idx = mapping[f] ?? -1;
                    return (
                      <div key={f} className="grid gap-2">
                        <Label className="flex items-center gap-1.5">
                          {idx >= 0 ? <CheckCircle2 className="size-3.5 text-emerald-500" /> : <XCircle className="size-3.5 text-destructive" />}
                          {label}
                        </Label>
                        <Pick
                          value={String(idx)}
                          onChange={(v) => { setMapping((m) => ({ ...m, [f]: Number(v) })); setProcessed(null); }}
                          options={[{ value: UNSET, label: "— not mapped —" }, ...table.headers.map((h, i) => ({ value: String(i), label: h }))]}
                        />
                      </div>
                    );
                  })}
                </div>
                <div className="flex items-center gap-3">
                  <Button onClick={runProcess} disabled={missing.length > 0 || busy !== null}>
                    {busy === "process" && <Loader2 className="animate-spin" />} Validate & process
                  </Button>
                  {missing.length > 0 && (
                    <span className="text-sm text-muted-foreground">Map: {missing.join(", ")}</span>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ---------------- 2 · QC ---------------- */}
        <TabsContent value="qc" className="mt-4 grid gap-4">
          {processed && (
            <>
              <div className="flex flex-wrap items-center gap-2">
                {summary && <Badge variant="outline">{summary.message}</Badge>}
                <Badge variant={counts.ERROR ? "destructive" : "outline"}>{counts.ERROR} errors</Badge>
                <Badge variant="secondary">{counts.WARNING} warnings</Badge>
                <Button size="sm" className="ml-auto" onClick={() => setTab("curve")}>View curve</Button>
              </div>
              <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
                <Card>
                  <CardHeader><CardTitle>Processed measurements</CardTitle>
                    <CardDescription>Rows are flagged, never deleted. Click a row to inspect it.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ScrollArea className="h-96">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Row</TableHead>
                            {arr?.fields.map((f) => <TableHead key={f.name}>{f.label}</TableHead>)}
                            <TableHead>R (Ω)</TableHead><TableHead>K (m)</TableHead>
                            <TableHead>ρa (Ωm)</TableHead><TableHead>QC</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {rows.map((r) => (
                            <TableRow
                              key={r.source_row}
                              data-state={r.source_row === selected ? "selected" : undefined}
                              className="cursor-pointer"
                              onClick={() => setSelected(r.source_row)}
                            >
                              <TableCell>{r.source_row}</TableCell>
                              {arr?.fields.map((f) => <TableCell key={f.name} className="tabular-nums">{fmt(r[f.name])}</TableCell>)}
                              <TableCell className="tabular-nums">{fmt(r.resistance_ohm)}</TableCell>
                              <TableCell className="tabular-nums">{fmt(r.geometric_factor)}</TableCell>
                              <TableCell className="tabular-nums">{fmt(r.apparent_resistivity)}</TableCell>
                              <TableCell><StatusBadge s={r.qc_status} /></TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </ScrollArea>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle>Issues</CardTitle></CardHeader>
                  <CardContent>
                    <ScrollArea className="h-96">
                      <ul className="grid gap-2 pr-3 text-sm">
                        {issues.map((i, k) => (
                          <li key={k} className="flex gap-2">
                            <SeverityIcon s={i.severity} />
                            <span>
                              {i.message}
                              {i.row != null && (
                                <button className="ml-1 text-muted-foreground underline" onClick={() => setSelected(i.row)}>
                                  row {i.row}
                                </button>
                              )}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </ScrollArea>
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </TabsContent>

        {/* ---------------- 3 · CURVE ---------------- */}
        <TabsContent value="curve" className="mt-4 grid gap-4 lg:grid-cols-[1fr_320px]">
          <Card>
            <CardHeader>
              <CardTitle>Apparent resistivity vs spacing</CardTitle>
              <CardDescription>Log-log. Click a point to inspect it; zoom and pan with the toolbar.</CardDescription>
            </CardHeader>
            <CardContent className="h-[440px]">
              <CurveChart rows={rows} model={run} selected={selected} onSelect={setSelected} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Point inspector</CardTitle></CardHeader>
            <CardContent className="grid gap-3 text-sm">
              {sel ? (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Row {sel.source_row}</span>
                    <StatusBadge s={sel.qc_status} />
                  </div>
                  <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5">
                    {arr?.fields.map((f) => (
                      <div key={f.name} className="contents">
                        <dt className="text-muted-foreground">{f.label}</dt>
                        <dd className="text-right tabular-nums">{fmt(sel[f.name])}</dd>
                      </div>
                    ))}
                    <dt className="text-muted-foreground">Resistance</dt><dd className="text-right tabular-nums">{fmt(sel.resistance_ohm)} Ω</dd>
                    <dt className="text-muted-foreground">Geometric factor</dt><dd className="text-right tabular-nums">{fmt(sel.geometric_factor)} m</dd>
                    <dt className="text-muted-foreground">Apparent ρ</dt><dd className="text-right tabular-nums">{fmt(sel.apparent_resistivity)} Ωm</dd>
                  </dl>
                  <p className="text-xs text-muted-foreground">
                    ρa = K × R, with K from the {arr?.title} electrode geometry.
                  </p>
                  {issues.filter((i) => i.row === sel.source_row).map((i, k) => (
                    <p key={k} className="flex gap-2"><SeverityIcon s={i.severity} />{i.message}</p>
                  ))}
                </>
              ) : (
                <p className="text-muted-foreground">Select a point on the curve.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ---------------- 4 · INVERSION ---------------- */}
        <TabsContent value="inversion" className="mt-4 grid gap-4">
          <Card>
            <CardHeader>
              <CardTitle>1D inversion</CardTitle>
              <CardDescription>
                Each run is kept — changing a setting creates a new run, never overwrites the last one.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap items-end gap-4">
              <div className="grid gap-2">
                <Label>Layers</Label>
                <Pick value={nLayers} onChange={setNLayers} className="w-24"
                  options={[2, 3, 4, 5].map((n) => ({ value: String(n), label: String(n) }))} />
              </div>
              <div className="grid gap-2">
                <Label>Assumed data error (%)</Label>
                <Input className="w-32" type="number" min="0.1" step="0.5" value={errPct} onChange={(e) => setErrPct(e.target.value)} />
              </div>
              <Button onClick={runInvert} disabled={busy !== null || arrayId !== "schlumberger"}>
                {busy === "invert" && <Loader2 className="animate-spin" />} Run inversion
              </Button>
              {arrayId !== "schlumberger" && (
                <span className="text-sm text-muted-foreground">Inversion currently supports Schlumberger data only.</span>
              )}
            </CardContent>
          </Card>

          {notice && (
            <Alert>
              <Info />
              <AlertDescription>{notice}</AlertDescription>
            </Alert>
          )}
          {runs.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {runs.map((r, i) => (
                <Button key={`${i}-${r.run_id}`} size="sm" variant={i === activeRun ? "default" : "outline"} onClick={() => setActiveRun(i)}>
                  Run {i + 1} · {r.config.n_layers} layers · RMS {fmt(r.rms_percent, 3)}%
                </Button>
              ))}
            </div>
          )}

          {run && (
            <>
              <Alert>
                <Info />
                <AlertTitle>Interpret with care</AlertTitle>
                <AlertDescription>{run.warnings.join(" ")}</AlertDescription>
              </Alert>
              <div className="grid gap-4 lg:grid-cols-2">
                <Card>
                  <CardHeader><CardTitle>Observed vs model</CardTitle></CardHeader>
                  <CardContent className="h-80">
                    <CurveChart rows={rows} model={run} selected={selected} onSelect={setSelected} />
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle>Layer model</CardTitle></CardHeader>
                  <CardContent className="h-80"><LayerProfile result={run} /></CardContent>
                </Card>
              </div>
              <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
                <Card>
                  <CardHeader><CardTitle>Layers</CardTitle></CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow><TableHead>#</TableHead><TableHead>ρ (Ωm)</TableHead><TableHead>Thickness (m)</TableHead>
                          <TableHead>Top (m)</TableHead><TableHead>Bottom (m)</TableHead></TableRow>
                      </TableHeader>
                      <TableBody>
                        {run.resistivity.map((rho, i) => (
                          <TableRow key={i}>
                            <TableCell>{i + 1}</TableCell>
                            <TableCell className="tabular-nums">{fmt(rho)}</TableCell>
                            <TableCell className="tabular-nums">{i < run.thickness.length ? fmt(run.thickness[i]) : "half-space"}</TableCell>
                            <TableCell className="tabular-nums">{fmt(run.depth_top[i])}</TableCell>
                            <TableCell className="tabular-nums">{run.depth_bottom[i] == null ? "∞" : fmt(run.depth_bottom[i])}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle>Fit quality</CardTitle></CardHeader>
                  <CardContent className="grid gap-2 text-sm">
                    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5">
                      <dt className="text-muted-foreground">RMS</dt><dd className="text-right tabular-nums">{fmt(run.rms_percent, 3)} %</dd>
                      <dt className="text-muted-foreground">χ²</dt><dd className="text-right tabular-nums">{fmt(run.chi2, 3)}</dd>
                      <dt className="text-muted-foreground">Iterations</dt><dd className="text-right tabular-nums">{run.iterations}</dd>
                      <dt className="text-muted-foreground">Converged</dt><dd className="text-right">{run.converged ? "yes (χ² ≤ 1)" : "no (χ² > 1)"}</dd>
                      <dt className="text-muted-foreground">Run ID</dt><dd className="text-right">{run.run_id}</dd>
                      <dt className="text-muted-foreground">Engine</dt><dd className="text-right">v{String(run.metadata.engine_version)}</dd>
                      <dt className="text-muted-foreground">pyGIMLi</dt><dd className="text-right">{String(run.metadata.pygimli)}</dd>
                    </dl>
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
