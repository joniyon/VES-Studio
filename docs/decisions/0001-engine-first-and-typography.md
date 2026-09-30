# 0001 — Engine first; monospace UI typography

- **Engine first.** Per the scope (Phase 0–1), no UI work before the scientific engine has validated
  arrays, units, validation and QC. Frontend (`apps/web`) is scaffolded empty.
- **Monospace font** for the UI (numbers, tables, data readouts). Specific font pending — user will supply files.
- **pyGIMLi** deferred: `pgcore` has no wheel for Python 3.13. Inversion service will need a 3.11/3.12 environment.
- Data mapping and file upload (CSV/XLSX) belong to Phase 2; the engine accepts a DataFrame with canonical column names.
