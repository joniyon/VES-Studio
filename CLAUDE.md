# VES Studio: standing rules

Open-source-first platform for Vertical Electrical Sounding (VES): processing, QC, 1D inversion, reporting.
Frontend `apps/web` (Next.js, shadcn/ui, Geist Mono, Plotly). Engine `services/geophysics-api` (FastAPI, pyGIMLi).
No accounts or database: state lives in the browser (autosave) and in portable `*.ves.json` project files.
Current behaviour of every screen: `docs/product/app-flows.md`. Acceptance status: `docs/product/v1-acceptance.md`.

## UI target
`docs/ui-reference.png` shows the layout pattern to follow: slim top menu bar, sub-bar with pill actions, left icon
tool rail, central canvas as the hero, right icon rail opening floating cards, bottom-left monospace status panel,
bottom-right zoom control, bottom-centre toasts. Adapt it to VES. It is a layout reference, not a domain reference
(the screenshot is a different product).

## Design system
- Neutral slate surfaces, one accent (teal), red errors, amber warnings, green valid.
- Geist Sans for UI, Geist Mono for numbers, tables and IDs. 8px grid, 8-12px radius on panels, soft shadows on
  floating panels only, 1px borders elsewhere, 150ms ease micro-interactions.
- Light and dark themes (follow system by default). Icon buttons need tooltips and ARIA labels. Keyboard accessible.
- Responsive: rails collapse to icons on tablet; phone is a read-only viewer.

## Non-negotiable rules
1. Do not rewrite the engine. The real inversion always comes from `POST /invert`. Any browser-side forward model is
   only for live preview and must be labelled "preview".
2. Never remove or hide the honest caveats: results unvalidated against WinResist and published examples; lithology
   ranges unverified; VES inversion is non-unique, so always show ranges next to layer values and never present one
   confident table; raw-data misfit of 10 % or more is normal on field data; persistence is browser + project file
   only; point-electrode K differs from exact K by about 7 % at AB/2 = 1.
3. Units are never assumed silently. Nothing is silently dropped from data.
4. Every inversion run is kept; never overwrite. One run is "active" and drives plot, table, interpretation and report.
5. Existing features must keep working. Run lint, type-check and tests after every stage and fix failures before
   reporting.
6. Work in small commits, one per logical change. At the end of each stage, stop, summarise what changed, list anything
   unfinished, and wait for the go-ahead.

## Repo rules (already in force)
- `docs/architecture/engine-boundary.md`: `apps/web` never imports engine code. Rule 1 above grants one exception, a
  labelled browser-side preview model; everything else in that document still holds. UI needs are met by thin adapters in
  `app/api`; numerical modules are not edited for presentation reasons.
- `.githooks/pre-commit` blocks commits that mix `apps/web` with engine files (`services/geophysics-api/app|tests`,
  `scientific/`) and runs the engine tests on `app/` changes. Split the commit; do not set `ENGINE_CHANGE=1` to bypass.
- Every engine change bumps `ENGINE_VERSION` (`app/__init__.py`) and `pyproject.toml` together (now 0.6.0).
- pyGIMLi is imported only in `app/inversion/pygimli_backend.py`.
- `data/` (field data) is git-ignored and private. Do not commit it or paste it into docs.
- `apps/web/AGENTS.md`: this Next.js version has breaking changes; read the relevant guide in
  `apps/web/node_modules/next/dist/docs/` before writing Next.js code.
- shadcn components here sit on `@base-ui/react` (not Radix): polymorphism is `render={...}` (+ `nativeButton`).
- ADR `docs/decisions/0001` chose all-monospace UI type. The Design system section above supersedes it (Sans for UI,
  Mono for data); the app is still all Geist Mono until the redesign lands.

## Commands
Run from the repo root.
```
# Engine tests (also run by the pre-commit hook)
cd services/geophysics-api && DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/opt/lapack/lib .venv/bin/python -m pytest -q
# API (port 8000)
cd services/geophysics-api && DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/opt/lapack/lib .venv/bin/python -m uvicorn app.api.main:app --port 8000
# Web (port 3000)
cd apps/web && npm run dev
# Web checks
cd apps/web && npm run lint && npx tsc --noEmit
```
- pyGIMLi needs `DYLD_FALLBACK_LIBRARY_PATH` (macOS SIP strips it through `nohup`; do not launch Python under `nohup`).
- There are no frontend tests yet; `lint` + `tsc` are the frontend gate. Verify UI changes in the browser.
- Inversions take about 3-5 s (multi-start + equivalence sampling). `VES_EQUIVALENCE_SAMPLES` sets the default sample
  count (the test suite uses 200; production 3000).
- Scratch files go in the session scratchpad, not the repo. pyGIMLi failures drop `*Nan*.vector` files in the working
  directory; delete them, never commit them.
