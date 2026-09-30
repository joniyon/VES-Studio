# 0001 — Engine first; monospace UI typography

- **Engine first.** Per the scope (Phase 0–1), no UI work before the scientific engine has validated
  arrays, units, validation and QC. Frontend (`apps/web`) is scaffolded empty.
- **Monospace font** for the UI (numbers, tables, data readouts). Specific font pending — user will supply files.
- **pyGIMLi** runs on Python 3.12 (no 3.13 wheel for pgcore); needs `brew install lapack` on macOS.
- Data mapping and file upload (CSV/XLSX) belong to Phase 2; the engine accepts a DataFrame with canonical column names.
- **ResIPy** (evaluated 2026): installs via pip but needs Wine on macOS to run its R2 executables and targets
  2D/3D ERT, not 1D VES geometric factors. Deferred to V2 (pseudo-sections / 2D). pyGIMLi remains the
  independent cross-check for V1.
