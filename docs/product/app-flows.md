# VES Studio: what the app does today (UI context)

Engine v0.6.0. Web app: Next.js + shadcn/ui + Geist Mono, a single-page workspace (`apps/web/components/workspace.tsx`)
talking to a FastAPI engine (`services/geophysics-api`). No accounts or database: work lives in the browser
(autosave) and in portable project files (`*.ves.json`).

## Flow: seven tabs, left to right
Later tabs unlock as work progresses (QC/Curve/Inversion need processed data; Interpretation needs an inversion run).

| Tab | What the user does | Key outputs / states |
|---|---|---|
| **0 Project** | Name, location, client, researcher, survey date, status; VES station (id, lat/long with validation, elevation, notes); save/open/new project file | Processing history log (every action timestamped); autosave |
| **1 Data** | Choose electrode array and units; choose what was measured (resistance / voltage+current / apparent resistivity); upload CSV or XLSX (sheet picker) or load the built-in synthetic sample; map columns (auto-detected, ✓/✗ per field); toggle "MN/2 unknown (point electrodes)" and "MN column is full MN"; press Process | Original file kept with SHA-256; units never assumed silently |
| **2 QC** | Review processed table (ρa, K, QC status per row); read issues; exclude / restore points | Row status PASS / WARNING / ERROR / EXCLUDED, INFO/WARNING/ERROR issues, nothing silently dropped |
| **3 Curve** | Log-log apparent resistivity vs spacing (hover, click-to-inspect, zoom/pan); point inspector; **Data preparation** card | Presets: Raw data, Average + Hanning, Average + median; manual overlap handling (none / average / shift + anchor), smoothing (none / median / Hanning), window 3 or 5; live preview of the prepared "working curve" |
| **4 Inversion** | Choose layers (2-7) and assumed data error (%); Run inversion; each run is kept and listed as a chip (never overwritten) | Observed vs model plot, resistivity-depth profile, layer table, fit-quality card (below) |
| **5 Interpretation** | Per layer: ranked lithology suggestions (not a verdict), pick lithology, set confidence; geological column figure; geological context; draft/edit conclusion | Lithology catalogue with colours/hatches, `verified=False` ranges flagged |
| **6 Report & export** | One-click exports | PDF report; processed CSV; layer CSV; inversion JSON; curve PNG/SVG; geological-column PNG/SVG; project file |

Arrays supported: Schlumberger, Wenner, pole-pole (sounding arrays: working curve and 1D inversion are meaningful);
dipole-dipole, pole-dipole, gradient (profiling arrays: inversion works but the UI/report warns it is of limited meaning
as a single-location 1D model). Working-curve preparation is available for sounding arrays only.

## What an inversion run returns (what the Inversion tab shows)
- **Layer table:** ρ, thickness, top, bottom (last layer is a half-space) **+ new:** ρ range and depth-to-top range
  of equivalent models (all models that fit as well as the best, 95 % region; `*` = range reaches the resistivity limit,
  i.e. not constrained by the data). If points <= parameters it says "cannot constrain" instead.
- **Fit quality:** RMS on the fitted (working) curve and on the raw data, points fitted (n of n_raw), χ², iterations,
  **optimiser finished** (yes/no) and **fit within assumed error** (χ² <= 1, usually "no" on noisy field data),
  starts tried and the regularisation that won, run ID, engine and pyGIMLi versions.
- **Warnings:** non-uniqueness note; working-curve note (shows both misfits: preparation can hide real structure).
- **Behaviour to design around:** a run takes about 3-5 s (multi-start search + equivalence sampling), so it needs a
  busy state. Several runs coexist; one is "active" and drives the plot, table, interpretation and report.

## Charts
Observed vs model (observed, observed-with-warning, excluded, working curve, model response), resistivity-depth layer
profile, geological column, lithology legend. Plotly (log axes labelled 1-2-5 in full). Light/dark theme toggle.

## API surface (for any new front end)
`GET /health`, `/arrays`, `/lithologies`, `/figures/legend`; `POST /process`, `/working-curve`, `/invert`,
`/suggest-lithology`, `/draft-summary`, `/parse-xlsx`, `/figures/curve`, `/figures/column`,
`/export/processed.csv`, `/export/layers.csv`, `/report.pdf`. Interactive docs at `http://localhost:8000/docs`.

## Known limits and honest caveats the UI should keep visible
- Results are unvalidated against WinResist and published examples; lithology resistivity ranges are unverified.
- VES inversion is non-unique: show ranges next to every layer value; never present one confident table.
- Real field data are noisy: raw-data misfit of 10 % or more is normal on field soundings.
- Persistence is browser + project file only. No accounts, no server-side projects.
- Apparent resistivity "reported" by other tools may use the point-electrode K (differs from exact K by ~7 % at
  AB/2 = 1).
