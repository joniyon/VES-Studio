# VES Studio

Open-source-first platform for Vertical Electrical Sounding processing, QC, 1D inversion and reporting.
Scope: [docs/product/ves-studio-scope.rtf](docs/product/ves-studio-scope.rtf).

## Status: Phase 1 — scientific engine (in progress)
Done: six electrode arrays, geometric factors, unit handling, validation/QC, apparent resistivity with lineage, 59 tests, pyGIMLi cross-check, layered forward model.
Next: 1D inversion wrapper (pyGIMLi abstraction), published-example validation, then Phase 2 foundation.

## Run tests
    cd services/geophysics-api
    brew install python@3.12 lapack
    /opt/homebrew/bin/python3.12 -m venv .venv
    .venv/bin/pip install numpy pandas scipy openpyxl pytest pygimli
    DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/opt/lapack/lib .venv/bin/python -m pytest -q
