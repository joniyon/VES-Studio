# VES Studio

Open-source-first platform for Vertical Electrical Sounding processing, QC, 1D inversion and reporting.
Scope: [docs/product/ves-studio-scope.rtf](docs/product/ves-studio-scope.rtf).

## Status: Phase 1 — scientific engine (in progress)
Done: six electrode arrays, geometric factors, unit handling, validation/QC, apparent resistivity with lineage, 47 tests.
Next: independent cross-check (pyGIMLi), benchmark datasets, then Phase 2 foundation.

## Run tests
    cd services/geophysics-api
    python3 -m venv .venv && .venv/bin/pip install numpy pandas scipy openpyxl pytest
    .venv/bin/python -m pytest -q
