"""Thin HTTP adapter over the engine. No science lives here."""
import math
from dataclasses import asdict

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app import ENGINE_VERSION
from app.arrays import REGISTRY, get_array
from app.inversion import InversionConfig, InversionError, invert_station
from app.processing import process_dataset
from app.units import CURRENT, DISTANCE, RESISTANCE, VOLTAGE

app = FastAPI(title="VES Studio geophysics API", version=ENGINE_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
                   allow_methods=["*"], allow_headers=["*"])

FIELD_LABELS = {
    "ab_half": "AB/2", "mn_half": "MN/2", "a": "a (spacing)", "n": "n (separation factor)",
    "ab": "AB", "mn": "MN", "x": "x (MN centre offset)",
}
ARRAY_TITLES = {
    "schlumberger": "Schlumberger", "wenner": "Wenner", "dipole_dipole": "Dipole-dipole",
    "pole_dipole": "Pole-dipole", "pole_pole": "Pole-pole", "gradient": "Gradient / rectangle",
}


def clean(v):
    """Make engine output JSON-safe: NaN/inf -> None, numpy -> python."""
    if isinstance(v, dict):
        return {k: clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if hasattr(v, "tolist"):
        return clean(v.tolist())
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


class Dataset(BaseModel):
    array: str
    units: dict[str, str] = Field(default_factory=dict)
    rows: list[dict]


class InvertRequest(Dataset):
    config: dict = Field(default_factory=dict)


@app.exception_handler(ValueError)
async def value_error(_, exc: ValueError):
    return JSONResponse({"error": str(exc)}, status_code=422)


@app.get("/health")
def health():
    return {"status": "ok", "engine_version": ENGINE_VERSION}


@app.get("/arrays")
def arrays():
    return {
        "arrays": [
            {"id": k, "title": ARRAY_TITLES[k],
             "fields": [{"name": f, "label": FIELD_LABELS[f], "kind": "distance"} for f in a.required_fields]
                       + [{"name": f, "label": FIELD_LABELS[f], "kind": "integer"} for f in a.integer_fields],
             "references": list(a.references)}
            for k, a in REGISTRY.items()
        ],
        "units": {"distance": list(DISTANCE), "resistance": list(RESISTANCE),
                  "voltage": list(VOLTAGE), "current": list(CURRENT)},
    }


def _process(req: Dataset):
    get_array(req.array)  # raises ValueError -> 422
    return process_dataset(pd.DataFrame(req.rows), req.array, req.units)


@app.post("/process")
def process(req: Dataset):
    res = _process(req)
    return clean({
        "rows": res.table.to_dict(orient="records"),
        "issues": [{**asdict(i), "severity": i.severity.value} for i in res.issues],
        "has_errors": res.has_errors,
        "lineage": res.lineage,
    })


@app.post("/invert")
def invert(req: InvertRequest):
    res = _process(req)
    if res.table.empty:
        return clean({"error": "; ".join(i.message for i in res.issues)})
    cfg = InversionConfig(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in req.config.items()})
    try:
        r = invert_station(res, cfg)
    except InversionError as e:
        return clean({"error": str(e)})
    d = asdict(r)
    d["config"] = asdict(r.config)
    return clean(d)
