# VES Studio

Open-source-first platform for Vertical Electrical Sounding processing, QC, 1D inversion and reporting.
Scope: [docs/product/ves-studio-scope.rtf](docs/product/ves-studio-scope.rtf).

## Status: V1 feature-complete except real-data validation
See [docs/product/v1-acceptance.md](docs/product/v1-acceptance.md) for the checklist against the scope, including
what is still unverified (real field dataset, reference/range verification, published examples).

## Run tests
    cd services/geophysics-api
    brew install python@3.12 lapack
    /opt/homebrew/bin/python3.12 -m venv .venv
    .venv/bin/pip install numpy pandas scipy openpyxl pytest pygimli
    DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/opt/lapack/lib .venv/bin/python -m pytest -q

## Run the app
    # API (port 8000)
    cd services/geophysics-api
    DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/opt/lapack/lib .venv/bin/python -m uvicorn app.api.main:app --port 8000
    # Web (port 3000) — Next.js + shadcn/ui + Geist Mono
    cd apps/web && npm install && npm run dev
