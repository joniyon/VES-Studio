"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, FlaskConical, Info, Loader2, Undo2, Upload, XCircle } from "lucide-react";
import {
  fetchBlob, getArrays, getLithologies, invert, parseXlsx, processData, suggestLithology,
  type ArrayMeta, type ArraysResponse, type InversionConfig, type InversionResult, type Issue,
  type LayerInterp, type LithologyResponse, type Payload, type ProcessResponse, type ProcessedRow,
  type Suggestion, type Units,
} from "@/lib/api";
import {
  EMPTY_PROJECT, EMPTY_STATION, clearSaved, download, loadSaved, parseProjectFile, save, sha256Hex, slug, toBase64,
  validateStation, type HistoryEvent, type ProjectMeta, type SavedState, type StationMeta, type UploadInfo,
} from "@/lib/project";
import { SAMPLE_CSV } from "@/lib/sample";
import { autoMap, buildRows, parseCsv, targetFields, type Mapping, type Measurement } from "@/lib/table";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CurveChart } from "./curve-chart";
import { ExportPanel, type ExportAction } from "./export-panel";
import { BLANK, InterpretationPanel } from "./interpretation-panel";
import { LayerProfile } from "./layer-profile";
import { Pick } from "./pick";
import { ProjectPanel } from "./project-panel";
import { ThemeToggle } from "./theme-toggle";

const fmt = (v: unknown, d = 4) =>
  typeof v === "number" ? (Math.abs(v) >= 1e4 || (v !== 0 && Math.abs(v) < 1e-2) ? v.toExponential(3) : Number(v.toPrecision(d)).toString()) : "—";

const DEFAULT_UNITS: Units = { distance: "m", resistance: "ohm", voltage: "V", current: "A", resistivity: "ohm-m" };
const UNSET = "-1";
const MEASURE_LABELS: Record<string, string> = {
  resistance: "Resistance", voltage: "Voltage", current: "Current", apparent_resistivity: "Apparent resistivity",
};
const now = () => new Date().toISOString();

type RunRecord = { result: InversionResult; excluded: number[] };

function SeverityIcon({ s }: { s: Issue["severity"] }) {
  if (s === "ERROR") return <XCircle className="size-4 shrink-0 text-destructive" />;
  if (s === "WARNING") return <AlertTriangle className="size-4 shrink-0 text-amber-500" />;
  return <Info className="size-4 shrink-0 text-muted-foreground" />;
}

function StatusBadge({ s }: { s: string }) {
  return <Badge variant={s === "ERROR" ? "destructive" : s === "WARNING" ? "secondary" : "outline"}>{s}</Badge>;
}

export function Workspace() {
  const [meta, setMeta] = useState<ArraysResponse | null>(null);
  const [litMeta, setLitMeta] = useState<LithologyResponse | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const [project, setProject] = useState<ProjectMeta>(EMPTY_PROJECT);
  const [station, setStation] = useState<StationMeta>(EMPTY_STATION);
  const [arrayId, setArrayId] = useState("schlumberger");
  const [units, setUnits] = useState<Units>(DEFAULT_UNITS);
  const [measurement, setMeasurement] = useState<Measurement>("r");
  const [assumeMn, setAssumeMn] = useState(false);
  const [upload, setUpload] = useState<UploadInfo | null>(null);
  const [sheets, setSheets] = useState<string[]>([]);
  const fileRef = useRef<File | null>(null);
  const [mapping, setMapping] = useState<Mapping>({});
  const [excluded, setExcluded] = useState<number[]>([]);
  const [processed, setProcessed] = useState<ProcessResponse | null>(null);
  const [runs, setRunsState] = useState<RunRecord[]>([]);
  const runsRef = useRef<RunRecord[]>([]);
  const inFlight = useRef(false);
  const setRuns = useCallback((next: RunRecord[]) => { runsRef.current = next; setRunsState(next); }, []);
  const [activeRun, setActiveRun] = useState<number | null>(null);
  const [nLayers, setNLayers] = useState("3");
  const [errPct, setErrPct] = useState("3");
  const [interpretation, setInterpretation] = useState<Record<string, LayerInterp[]>>({});
  const [context, setContext] = useState("");
  const [conclusion, setConclusion] = useState("");
  const [history, setHistory] = useState<HistoryEvent[]>([]);
  const [sugState, setSugState] = useState<{ id: string; data: Suggestion[][] } | null>(null);
  const [columnUrl, setColumnUrl] = useState<string | null>(null);
  const [columnError, setColumnError] = useState<string | null>(null);

  const [selected, setSelected] = useState<number | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [exportMsg, setExportMsg] = useState<string | null>(null);
  const [tab, setTab] = useState("project");
  const [hydrated, setHydrated] = useState(false);

  const log = useCallback((text: string) => setHistory((h) => [...h, { t: now(), text }]), []);

  useEffect(() => {
    getArrays().then(setMeta).catch((e: Error) => setApiError(e.message));
    getLithologies().then(setLitMeta).catch(() => {});
  }, []);

  const arr: ArrayMeta | undefined = meta?.arrays.find((a) => a.id === arrayId);
  const mnAssumable = arrayId === "schlumberger";
  const fields = useMemo(() => (arr ? targetFields(arr, measurement, assumeMn && mnAssumable) : []), [arr, measurement, assumeMn, mnAssumable]);
  const table = upload?.table ?? null;
  const missing = fields.filter((f) => (mapping[f] ?? -1) < 0);
  const stationErrors = useMemo(() => validateStation(station), [station]);

  const payload = useCallback((excl: number[] = excluded): Payload => ({
    array: arrayId, units, rows: table ? buildRows(table, mapping, fields) : [], excluded_rows: excl,
    assume_point_mn: assumeMn && mnAssumable,
  }), [arrayId, units, table, mapping, fields, excluded, assumeMn, mnAssumable]);

  const run = activeRun != null ? (runs[activeRun] ?? null) : null;
  const runId = run?.result.run_id ?? null;
  const interp: LayerInterp[] = useMemo(() => {
    if (!run) return [];
    const cur = interpretation[run.result.run_id] ?? [];
    return run.result.resistivity.map((_, i) => cur[i] ?? BLANK);
  }, [run, interpretation]);

  // ------------------------------------------------------------------ data loading
  const resetResults = useCallback(() => {
    setProcessed(null); setRuns([]); setActiveRun(null); setSelected(null); setNotice(null);
    setSugState(null); setColumnUrl(null);
  }, [setRuns]);

  const setUploaded = (info: UploadInfo, nextArr = arr, mode: Measurement = measurement, mn = assumeMn) => {
    setUpload(info);
    setExcluded([]);
    resetResults();
    setError(null);
    if (nextArr) setMapping(autoMap(info.table.headers, targetFields(nextArr, mode, mn && nextArr.id === "schlumberger")));
    log(`Loaded ${info.file_name} (${info.table.rows.length} rows, SHA-256 ${info.sha256.slice(0, 12)}…)`);
    setTab("data");
  };

  const onFile = async (f: File | undefined) => {
    if (!f) return;
    setError(null);
    try {
      if (/\.xlsx$/i.test(f.name)) {
        const buf = await f.arrayBuffer();
        const sha = await sha256Hex(buf);
        fileRef.current = f;
        const r = await parseXlsx(f);
        setSheets(r.sheets);
        setUploaded({ file_name: f.name, sha256: sha, sheet: r.sheet, table: { headers: r.headers, rows: r.rows },
          original: { kind: "base64", data: toBase64(buf) } });
      } else if (/\.(csv|txt)$/i.test(f.name)) {
        const text = await f.text();
        fileRef.current = null; setSheets([]);
        setUploaded({ file_name: f.name, sha256: await sha256Hex(text), table: parseCsv(text), original: { kind: "text", data: text } });
      } else {
        setError("Unsupported file type. Use .csv or .xlsx.");
      }
    } catch (e) { setError((e as Error).message); }
  };

  const changeSheet = async (name: string) => {
    if (!fileRef.current || !upload) return;
    try {
      const r = await parseXlsx(fileRef.current, name);
      setUploaded({ ...upload, sheet: r.sheet, table: { headers: r.headers, rows: r.rows } });
    } catch (e) { setError((e as Error).message); }
  };

  const loadSample = async () => {
    fileRef.current = null; setSheets([]);
    const sa = meta?.arrays.find((a) => a.id === "schlumberger");
    setArrayId("schlumberger"); setMeasurement("r"); setAssumeMn(false); setUnits(DEFAULT_UNITS);
    setUploaded({ file_name: "synthetic_schlumberger_3layer.csv", sha256: await sha256Hex(SAMPLE_CSV),
      table: parseCsv(SAMPLE_CSV), original: { kind: "text", data: SAMPLE_CSV } }, sa, "r", false);
  };

  const remap = (nextArr: ArrayMeta | undefined, mode: Measurement, mn = assumeMn) => {
    if (table && nextArr) setMapping(autoMap(table.headers, targetFields(nextArr, mode, mn && nextArr.id === "schlumberger")));
    resetResults();
  };

  // ------------------------------------------------------------------ processing / inversion
  const runProcess = async (excl: number[] = excluded, silent = false) => {
    setBusy("process"); setError(null);
    try {
      const res = await processData(payload(excl));
      setProcessed(res);
      if (!silent) {
        const e = res.issues.filter((i) => i.severity === "ERROR").length;
        const w = res.issues.filter((i) => i.severity === "WARNING").length;
        log(`Validated & processed with engine v${String(res.lineage.engine_version)}: ${res.rows.length} rows, ${e} errors, ${w} warnings`);
        setRuns([]); setActiveRun(null);
        setTab("qc");
      }
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(null); }
  };

  const toggleExclude = async (row: number) => {
    const next = excluded.includes(row) ? excluded.filter((r) => r !== row) : [...excluded, row].sort((a, b) => a - b);
    setExcluded(next);
    log(`${next.includes(row) ? "Excluded" : "Re-included"} row ${row}`);
    await runProcess(next, true);
    if (runs.length) setNotice("Exclusions changed. Earlier inversion runs are kept; run the inversion again to use the new selection.");
  };

  const runInvert = async () => {
    if (inFlight.current) return;            // never run two inversions at once
    inFlight.current = true;
    setBusy("invert"); setError(null);
    try {
      const config: InversionConfig = { n_layers: Number(nLayers), error_percent: Number(errPct) };
      const res = await invert({ ...payload(), config });
      const cur = runsRef.current;           // authoritative list (not a stale render closure)
      const existing = cur.findIndex((r) => r.result.run_id === res.run_id);
      if (existing >= 0) {
        setActiveRun(existing);
        setNotice(`Same data and settings as Run ${existing + 1} — the result is identical (reproducible).`);
      } else {
        const next = [...cur, { result: res, excluded: [...excluded] }];
        setRuns(next);
        setActiveRun(next.length - 1);
        setNotice(null);
        log(`Inversion run ${next.length}: ${res.config.n_layers} layers, error ${res.config.error_percent}%, RMS ${res.rms_percent.toFixed(2)}%, run ${res.run_id}`);
      }
    } catch (e) { setError((e as Error).message); }
    finally { inFlight.current = false; setBusy(null); }
  };

  // ------------------------------------------------------------------ interpretation
  useEffect(() => {
    if (!run) return;
    const r = run.result;
    let cancelled = false;
    suggestLithology(r.resistivity.map((rho, i) => ({ resistivity: rho, depth_top: r.depth_top[i], depth_bottom: r.depth_bottom[i] })))
      .then((s) => { if (!cancelled) setSugState({ id: r.run_id, data: s.layers }); })
      .catch(() => { if (!cancelled) setSugState(null); });
    return () => { cancelled = true; };
  }, [run]);
  const suggestions: Suggestion[][] = sugState && sugState.id === runId ? sugState.data : [];

  const setLayerInterp = (i: number, patch: Partial<LayerInterp>) => {
    if (!run) return;
    const id = run.result.run_id;
    setInterpretation((all) => {
      const cur = run.result.resistivity.map((_, k) => all[id]?.[k] ?? BLANK);
      cur[i] = { ...cur[i], ...patch };
      return { ...all, [id]: cur };
    });
  };

  const runPayload = useCallback((r: RunRecord) => ({ ...payload(r.excluded), config: r.result.config }), [payload]);

  // column figure (debounced) for the active run
  useEffect(() => {
    if (!run || tab !== "interpretation") return;
    let url: string | null = null;
    let cancelled = false;
    const t = setTimeout(async () => {
      try {
        const blob = await fetchBlob("/figures/column", { ...runPayload(run), interpretation: interp });
        if (cancelled) return;
        url = URL.createObjectURL(blob);
        setColumnUrl((old) => { if (old) URL.revokeObjectURL(old); return url; });
        setColumnError(null);
      } catch (e) { if (!cancelled) setColumnError((e as Error).message); }
    }, 350);
    return () => { cancelled = true; clearTimeout(t); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, interp, tab]);

  const draftConclusion = async () => {
    if (!run) return;
    try {
      const r = await fetch(`${(await import("@/lib/api")).API_URL}/draft-summary`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...runPayload(run), interpretation: interp }),
      });
      setConclusion((await r.json()).summary ?? "");
    } catch (e) { setError((e as Error).message); }
  };

  // ------------------------------------------------------------------ persistence
  const snapshot = useCallback((): SavedState => ({
    format: "ves-studio-project", version: 1, saved_at: now(), project, station, upload, arrayId, units, useVI: measurement === "vi", measurement, assumeMn, mapping,
    excluded, runs: runs.map((r) => ({ config: r.result.config, excluded: r.excluded })), activeRun, interpretation,
    geologicalContext: context, conclusion, history,
  }), [project, station, upload, arrayId, units, measurement, assumeMn, mapping, excluded, runs, activeRun, interpretation, context, conclusion, history]);

  const applyState = useCallback(async (s: SavedState, from: "session" | "file") => {
    setProject(s.project); setStation(s.station); setUpload(s.upload); setArrayId(s.arrayId);
    const mode: Measurement = s.measurement ?? (s.useVI ? "vi" : "r");
    setMeasurement(mode); setAssumeMn(!!s.assumeMn); setUnits({ ...DEFAULT_UNITS, ...s.units }); setMapping(s.mapping); setExcluded(s.excluded); setInterpretation(s.interpretation);
    setContext(s.geologicalContext); setConclusion(s.conclusion); setHistory(s.history);
    setSheets([]); fileRef.current = null;
    resetResults();
    if (!s.upload) return;
    // Recompute results deterministically from the saved inputs.
    try {
      const arrMeta = (await getArrays()).arrays.find((a) => a.id === s.arrayId);
      if (!arrMeta) return;
      const mn = !!s.assumeMn && s.arrayId === "schlumberger";
      const fs = targetFields(arrMeta, mode, mn);
      const base = { array: s.arrayId, units: { ...DEFAULT_UNITS, ...s.units }, rows: buildRows(s.upload.table, s.mapping, fs), assume_point_mn: mn };
      setProcessed(await processData({ ...base, excluded_rows: s.excluded }));
      const restored: RunRecord[] = [];
      for (const r of s.runs) restored.push({ result: await invert({ ...base, excluded_rows: r.excluded, config: r.config }), excluded: r.excluded });
      setRuns(restored);
      setActiveRun(s.activeRun != null && s.activeRun < restored.length ? s.activeRun : restored.length ? restored.length - 1 : null);
      setNotice(from === "file" ? "Project file opened; results were recomputed from the saved data." : "Restored your last session; results were recomputed from the saved data.");
      setTab(restored.length ? "inversion" : "data");
    } catch (e) { setError((e as Error).message); }
  }, [setRuns, resetResults]);

  useEffect(() => {
    // Deferred so restoring state is not a synchronous setState inside the effect.
    const id = setTimeout(() => {
      const saved = loadSaved();
      setHydrated(true);
      if (saved) applyState(saved, "session");
    }, 0);
    return () => clearTimeout(id);
  }, [applyState]);

  useEffect(() => {
    if (!hydrated) return;
    const t = setTimeout(() => save(snapshot()), 500);
    return () => clearTimeout(t);
  }, [hydrated, snapshot]);

  const importFile = async (f: File | undefined) => {
    if (!f) return;
    try { await applyState(parseProjectFile(await f.text()), "file"); } catch (e) { setError((e as Error).message); }
  };
  const newProject = () => {
    if (!window.confirm("Start a new project? The current one is removed from this browser (save a project file first if you need it).")) return;
    clearSaved();
    setProject(EMPTY_PROJECT); setStation(EMPTY_STATION); setUpload(null); setExcluded([]); setMapping({});
    setInterpretation({}); setContext(""); setConclusion(""); setHistory([]); setSheets([]); fileRef.current = null;
    setUnits(DEFAULT_UNITS); setMeasurement("r"); setAssumeMn(false); resetResults(); setError(null); setTab("project");
  };

  // ------------------------------------------------------------------ exports
  const base = `${slug(project.name || "ves")}_${slug(station.id)}`;
  const doExport = async (key: string, fn: () => Promise<void>) => {
    setBusy(key); setExportMsg(null); setError(null);
    try { await fn(); setExportMsg(`Saved ${key.includes(":") ? key.split(":")[1] : key}.`); log(`Exported ${key}`); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(null); }
  };
  const uploadInfo = () => ({ file_name: upload?.file_name, sha256: upload?.sha256, mapping: Object.fromEntries(fields.map((f) => [f, table?.headers[mapping[f]] ?? null])) });

  const actions: ExportAction[] = [
    { key: "pdf", label: "PDF report", hint: "Full interpretation report", needsRun: true, run: () => doExport("pdf", async () => {
      if (!run) return;
      download(await fetchBlob("/report.pdf", { ...runPayload(run), project: { ...project, researcher: project.researcher }, station,
        interpretation: interp, geological_context: context, conclusion, upload: uploadInfo() }), `${base}_report.pdf`);
    }) },
    { key: "csv:processed", label: "Processed data (CSV)", hint: "ρa, K, QC per measurement", needsRun: false, run: () => doExport("csv:processed", async () =>
      download(await fetchBlob("/export/processed.csv", payload()), `${base}_processed.csv`)) },
    { key: "csv:layers", label: "Layer model (CSV)", hint: "ρ, thickness, depth, lithology", needsRun: true, run: () => doExport("csv:layers", async () => {
      if (run) download(await fetchBlob("/export/layers.csv", { ...runPayload(run), interpretation: interp }), `${base}_layers.csv`);
    }) },
    { key: "json:inversion", label: "Inversion results (JSON)", hint: "All runs, settings, metadata", needsRun: true, run: () => doExport("json:inversion", async () =>
      download(new Blob([JSON.stringify(runs.map((r) => r.result), null, 2)], { type: "application/json" }), `${base}_inversion.json`)) },
    { key: "img:curve-png", label: "Curve figure (PNG)", hint: "Observed vs model", needsRun: false, run: () => doExport("img:curve-png", async () =>
      download(await fetchBlob("/figures/curve", { ...(run ? runPayload(run) : { ...payload(), config: {} }), with_model: !!run, interpretation: interp }), `${base}_curve.png`)) },
    { key: "img:curve-svg", label: "Curve figure (SVG)", hint: "Vector, for publication", needsRun: false, run: () => doExport("img:curve-svg", async () =>
      download(await fetchBlob("/figures/curve?fmt=svg", { ...(run ? runPayload(run) : { ...payload(), config: {} }), with_model: !!run, interpretation: interp }), `${base}_curve.svg`)) },
    { key: "img:column-png", label: "Geological column (PNG)", hint: "With lithology patterns", needsRun: true, run: () => doExport("img:column-png", async () => {
      if (run) download(await fetchBlob("/figures/column", { ...runPayload(run), interpretation: interp }), `${base}_column.png`);
    }) },
    { key: "img:column-svg", label: "Geological column (SVG)", hint: "Vector, for publication", needsRun: true, run: () => doExport("img:column-svg", async () => {
      if (run) download(await fetchBlob("/figures/column?fmt=svg", { ...runPayload(run), interpretation: interp }), `${base}_column.svg`);
    }) },
    { key: "json:project", label: "Project file", hint: "Original upload, settings, history", needsRun: false, run: () => doExport("json:project", async () =>
      download(new Blob([JSON.stringify(snapshot(), null, 2)], { type: "application/json" }), `${base}.ves.json`)) },
  ];

  // ------------------------------------------------------------------ derived
  const rows: ProcessedRow[] = processed?.rows ?? [];
  const issues = processed?.issues ?? [];
  const summary = issues.find((i) => i.code === "SUMMARY");
  const counts = { ERROR: issues.filter((i) => i.severity === "ERROR").length, WARNING: issues.filter((i) => i.severity === "WARNING").length };
  const sel = rows.find((r) => r.source_row === selected) ?? null;
  const r0 = run?.result ?? null;
  const excludeBtn = (row: number, status: string) =>
    status === "ERROR" ? null : (
      <Button size="xs" variant="outline" onClick={(e) => { e.stopPropagation(); toggleExclude(row); }}>
        {status === "EXCLUDED" ? <><Undo2 /> Include</> : "Exclude"}
      </Button>
    );

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-6">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">VES Studio</h1>
          <p className="text-sm text-muted-foreground">
            {project.name ? `${project.name} · ` : ""}Upload → array → map → validate → curve → invert → interpret → report
          </p>
        </div>
        <div className="flex items-center gap-2">
          {meta && <Badge variant="outline">API connected</Badge>}
          <ThemeToggle />
        </div>
      </header>

      {apiError && (
        <Alert variant="destructive"><XCircle /><AlertTitle>Geophysics API unavailable</AlertTitle><AlertDescription>{apiError}</AlertDescription></Alert>
      )}
      {error && (
        <Alert variant="destructive"><XCircle /><AlertTitle>Something went wrong</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>
      )}
      {notice && tab !== "inversion" && (
        <Alert><Info /><AlertDescription>{notice}</AlertDescription></Alert>
      )}

      <Tabs value={tab} onValueChange={(v) => setTab(String(v))}>
        <TabsList className="flex-wrap">
          <TabsTrigger value="project">0 · Project</TabsTrigger>
          <TabsTrigger value="data">1 · Data</TabsTrigger>
          <TabsTrigger value="qc" disabled={!processed}>2 · QC</TabsTrigger>
          <TabsTrigger value="curve" disabled={!processed}>3 · Curve</TabsTrigger>
          <TabsTrigger value="inversion" disabled={!processed}>4 · Inversion</TabsTrigger>
          <TabsTrigger value="interpretation" disabled={!run}>5 · Interpretation</TabsTrigger>
          <TabsTrigger value="export" disabled={!processed}>6 · Report & export</TabsTrigger>
        </TabsList>

        {/* ---------------- 0 · PROJECT ---------------- */}
        <TabsContent value="project" className="mt-4">
          <ProjectPanel project={project} station={station} errors={stationErrors} history={history}
            onProject={setProject} onStation={setStation} onNew={newProject} onImport={importFile}
            onExportFile={() => doExport("json:project", async () => download(new Blob([JSON.stringify(snapshot(), null, 2)], { type: "application/json" }), `${base}.ves.json`))} />
        </TabsContent>

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
                <Pick label="Electrode array" value={arrayId} onChange={(v) => { setArrayId(v); remap(meta?.arrays.find((a) => a.id === v), measurement); }}
                  options={(meta?.arrays ?? []).map((a) => ({ value: a.id, label: a.title }))} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                {(["distance", ...(measurement === "rho" ? ["resistivity"] : measurement === "vi" ? ["voltage", "current"] : ["resistance"])] as (keyof Units)[]).map((q) => (
                  <div key={q} className="grid gap-2">
                    <Label className="capitalize">{q}</Label>
                    <Pick label={`${q} unit`} value={units[q]} onChange={(v) => { setUnits((u) => ({ ...u, [q]: v })); setProcessed(null); }}
                      options={(meta?.units[q] ?? []).map((u) => ({ value: u, label: u }))} />
                  </div>
                ))}
              </div>
              <div className="grid gap-2">
                <Label>Measured quantity</Label>
                <Pick label="Measured quantity" value={measurement} onChange={(v) => { setMeasurement(v as Measurement); remap(arr, v as Measurement); }}
                  options={[{ value: "r", label: "Resistance" }, { value: "vi", label: "Voltage + current" }, { value: "rho", label: "Apparent resistivity (already calculated)" }]} />
              </div>
              {mnAssumable && (
                <label className="flex items-start gap-2 text-sm">
                  <Checkbox checked={assumeMn} onCheckedChange={(c) => { setAssumeMn(c === true); remap(arr, measurement, c === true); }} className="mt-0.5" />
                  <span>
                    MN/2 is not in my file — assume point electrodes
                    <span className="block text-xs text-muted-foreground">Recorded in the report. Supply MN/2 for finite-electrode accuracy.</span>
                  </span>
                </label>
              )}
              {arr && <p className="text-xs text-muted-foreground">References: {arr.references.join("; ")}</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Field data</CardTitle>
              <CardDescription>CSV or XLSX upload, or load a synthetic 3-layer Schlumberger sounding.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3">
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" nativeButton={false} render={<label />}>
                  <Upload /> Choose CSV / XLSX
                  <input type="file" accept=".csv,.txt,.xlsx" className="sr-only" onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ""; }} />
                </Button>
                <Button variant="outline" onClick={loadSample}><FlaskConical /> Load sample</Button>
              </div>
              {upload && table ? (
                <>
                  <p className="text-sm">
                    <span className="font-medium">{upload.file_name}</span>{" "}
                    <span className="text-muted-foreground">· {table.rows.length} rows · {table.headers.length} columns</span>
                  </p>
                  <p className="break-all text-xs text-muted-foreground">SHA-256 {upload.sha256}</p>
                  {sheets.length > 1 && (
                    <div className="grid gap-2">
                      <Label>Sheet</Label>
                      <Pick label="Sheet" value={upload.sheet ?? sheets[0]} onChange={changeSheet} options={sheets.map((s) => ({ value: s, label: s }))} />
                    </div>
                  )}
                  <ScrollArea className="h-44 rounded-md border">
                    <Table>
                      <TableHeader><TableRow>{table.headers.map((h, i) => <TableHead key={i}>{h}</TableHead>)}</TableRow></TableHeader>
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
                <CardDescription>Detected automatically — check each field is pointing at the right column.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4">
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {fields.map((f) => {
                    const label = arr.fields.find((x) => x.name === f)?.label ?? MEASURE_LABELS[f] ?? f;
                    const idx = mapping[f] ?? -1;
                    return (
                      <div key={f} className="grid gap-2">
                        <Label className="flex items-center gap-1.5">
                          {idx >= 0 ? <CheckCircle2 className="size-3.5 text-emerald-500" /> : <XCircle className="size-3.5 text-destructive" />}
                          {label}
                        </Label>
                        <Pick label={`Column for ${label}`} value={String(idx)} onChange={(v) => { setMapping((m) => ({ ...m, [f]: Number(v) })); setProcessed(null); }}
                          options={[{ value: UNSET, label: "— not mapped —" }, ...table.headers.map((h, i) => ({ value: String(i), label: h || `(column ${i + 1})` }))]} />
                      </div>
                    );
                  })}
                </div>
                <div className="flex items-center gap-3">
                  <Button onClick={() => runProcess()} disabled={missing.length > 0 || busy !== null}>
                    {busy === "process" && <Loader2 className="animate-spin" />} Validate & process
                  </Button>
                  {missing.length > 0 && <span className="text-sm text-muted-foreground">Map: {missing.join(", ")}</span>}
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
                {excluded.length > 0 && <Badge variant="outline">{excluded.length} excluded</Badge>}
                <Button size="sm" className="ml-auto" onClick={() => setTab("curve")}>View curve</Button>
              </div>
              <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
                <Card>
                  <CardHeader><CardTitle>Processed measurements</CardTitle>
                    <CardDescription>Rows are flagged, never deleted. Exclude a point to leave it out of the inversion (its value is kept).</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ScrollArea className="h-96">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Row</TableHead>
                            {arr?.fields.map((f) => <TableHead key={f.name}>{f.label}</TableHead>)}
                            <TableHead>R (Ω)</TableHead><TableHead>K (m)</TableHead>
                            <TableHead>ρa (Ωm)</TableHead><TableHead>QC</TableHead><TableHead />
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {rows.map((r) => (
                            <TableRow key={r.source_row} data-state={r.source_row === selected ? "selected" : undefined}
                              className="cursor-pointer" onClick={() => setSelected(r.source_row)}>
                              <TableCell>{r.source_row}</TableCell>
                              {arr?.fields.map((f) => <TableCell key={f.name} className="tabular-nums">{fmt(r[f.name])}</TableCell>)}
                              <TableCell className="tabular-nums">{fmt(r.resistance_ohm)}</TableCell>
                              <TableCell className="tabular-nums">{fmt(r.geometric_factor)}</TableCell>
                              <TableCell className="tabular-nums">{fmt(r.apparent_resistivity)}</TableCell>
                              <TableCell><StatusBadge s={r.qc_status} /></TableCell>
                              <TableCell>{excludeBtn(r.source_row, r.qc_status)}</TableCell>
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
                                <button className="ml-1 text-muted-foreground underline" onClick={() => setSelected(i.row)}>row {i.row}</button>
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
              <CurveChart rows={rows} model={r0} selected={selected} onSelect={setSelected} />
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
                  <p className="text-xs text-muted-foreground">ρa = K × R, with K from the {arr?.title} electrode geometry.</p>
                  {issues.filter((i) => i.row === sel.source_row).map((i, k) => (
                    <p key={k} className="flex gap-2"><SeverityIcon s={i.severity} />{i.message}</p>
                  ))}
                  {excludeBtn(sel.source_row, sel.qc_status)}
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
              <CardDescription>Each run is kept — changing a setting creates a new run, never overwrites the last one.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap items-end gap-4">
              <div className="grid gap-2">
                <Label>Layers</Label>
                <Pick label="Number of layers" value={nLayers} onChange={setNLayers} className="w-24" options={[2, 3, 4, 5].map((n) => ({ value: String(n), label: String(n) }))} />
              </div>
              <div className="grid gap-2">
                <Label>Assumed data error (%)</Label>
                <Input aria-label="Assumed data error (%)" className="w-32" type="number" min="0.1" step="0.5" value={errPct} onChange={(e) => setErrPct(e.target.value)} />
              </div>
              <Button onClick={runInvert} disabled={busy !== null}>
                {busy === "invert" && <Loader2 className="animate-spin" />} Run inversion
              </Button>
              {excluded.length > 0 && <span className="text-sm text-muted-foreground">{excluded.length} point(s) excluded</span>}
            </CardContent>
          </Card>

          {notice && <Alert><Info /><AlertDescription>{notice}</AlertDescription></Alert>}
          {runs.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {runs.map((r, i) => (
                <Button key={`${i}-${r.result.run_id}`} size="sm" variant={i === activeRun ? "default" : "outline"} onClick={() => setActiveRun(i)}>
                  Run {i + 1} · {r.result.config.n_layers} layers · RMS {fmt(r.result.rms_percent, 3)}%
                </Button>
              ))}
            </div>
          )}

          {r0 && (
            <>
              <Alert>
                <Info /><AlertTitle>Interpret with care</AlertTitle>
                <AlertDescription>{r0.warnings.join(" ")}</AlertDescription>
              </Alert>
              <div className="grid gap-4 lg:grid-cols-2">
                <Card>
                  <CardHeader><CardTitle>Observed vs model</CardTitle></CardHeader>
                  <CardContent className="h-80"><CurveChart rows={rows} model={r0} selected={selected} onSelect={setSelected} /></CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle>Layer model</CardTitle></CardHeader>
                  <CardContent className="h-80"><LayerProfile result={r0} /></CardContent>
                </Card>
              </div>
              <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
                <Card>
                  <CardHeader><CardTitle>Layers</CardTitle></CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow><TableHead>#</TableHead><TableHead>ρ (Ωm)</TableHead><TableHead>Thickness (m)</TableHead><TableHead>Top (m)</TableHead><TableHead>Bottom (m)</TableHead></TableRow>
                      </TableHeader>
                      <TableBody>
                        {r0.resistivity.map((rho, i) => (
                          <TableRow key={i}>
                            <TableCell>{i + 1}</TableCell>
                            <TableCell className="tabular-nums">{fmt(rho)}</TableCell>
                            <TableCell className="tabular-nums">{i < r0.thickness.length ? fmt(r0.thickness[i]) : "half-space"}</TableCell>
                            <TableCell className="tabular-nums">{fmt(r0.depth_top[i])}</TableCell>
                            <TableCell className="tabular-nums">{r0.depth_bottom[i] == null ? "∞" : fmt(r0.depth_bottom[i])}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                    <Button className="mt-3" size="sm" onClick={() => setTab("interpretation")}>Interpret layers →</Button>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle>Fit quality</CardTitle></CardHeader>
                  <CardContent className="grid gap-2 text-sm">
                    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5">
                      <dt className="text-muted-foreground">RMS</dt><dd className="text-right tabular-nums">{fmt(r0.rms_percent, 3)} %</dd>
                      <dt className="text-muted-foreground">χ²</dt><dd className="text-right tabular-nums">{fmt(r0.chi2, 3)}</dd>
                      <dt className="text-muted-foreground">Iterations</dt><dd className="text-right tabular-nums">{r0.iterations}</dd>
                      <dt className="text-muted-foreground">Converged</dt><dd className="text-right">{r0.converged ? "yes (χ² ≤ 1)" : "no (χ² > 1)"}</dd>
                      <dt className="text-muted-foreground">Run ID</dt><dd className="text-right">{r0.run_id}</dd>
                      <dt className="text-muted-foreground">Engine</dt><dd className="text-right">v{String(r0.metadata.engine_version)}</dd>
                      <dt className="text-muted-foreground">pyGIMLi</dt><dd className="text-right">{String(r0.metadata.pygimli)}</dd>
                    </dl>
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </TabsContent>

        {/* ---------------- 5 · INTERPRETATION ---------------- */}
        <TabsContent value="interpretation" className="mt-4">
          {r0 && litMeta && (
            <InterpretationPanel run={r0} lithologies={litMeta.lithologies} confidenceLevels={litMeta.confidence_levels}
              interp={interp} suggestions={suggestions} columnUrl={columnUrl} columnError={columnError}
              context={context} conclusion={conclusion} onInterp={setLayerInterp}
              onContext={setContext} onConclusion={setConclusion} onDraft={draftConclusion} />
          )}
        </TabsContent>

        {/* ---------------- 6 · EXPORT ---------------- */}
        <TabsContent value="export" className="mt-4">
          <ExportPanel actions={actions} hasRun={!!run} busy={busy} message={exportMsg} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
