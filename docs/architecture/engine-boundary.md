# Engine boundary

The scientific engine (`services/geophysics-api/app/{arrays,processing,quality,inversion}`, `scientific/`) is
the product's most valuable asset and is treated as a stable, versioned component.

Rules while the UI is built:
1. `apps/web` never imports engine code and never reimplements science. It talks to the engine only through
   the FastAPI service (next: `app/api`, with a generated OpenAPI schema as the contract).
2. Engine changes and UI changes go in separate commits — enforced by `.githooks/pre-commit`
   (override deliberately with `ENGINE_CHANGE=1`). Any commit touching `app/` runs the full engine test suite.
3. UI-driven needs (a new field, a new endpoint) are added to `app/api` as thin adapters over engine functions;
   the engine's numerical modules are not edited for presentation reasons.
4. Every engine change bumps `ENGINE_VERSION`; it is stored in every processing lineage and inversion run.
5. Releases are git-tagged (`engine-vX.Y.Z`) so the UI can be pinned to a known-good engine.
6. pyGIMLi is imported only in `app/inversion/pygimli_backend.py`.
