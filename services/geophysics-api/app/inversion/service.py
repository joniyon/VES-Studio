"""Inversion service: engine-owned abstraction over backends + immutable run history."""
import hashlib
import json
from dataclasses import asdict

import numpy as np
import pandas as pd

from app import ENGINE_VERSION
from app.processing import ProcessedDataset
from .pygimli_backend import PygimliBackend
from .types import InversionBackend, InversionConfig, InversionResult


class InversionError(ValueError):
    pass


def _run_id(spacing, mn, observed, cfg, array) -> str:
    h = hashlib.sha256()
    h.update(json.dumps({"cfg": asdict(cfg), "array": array, "engine": ENGINE_VERSION},
                        sort_keys=True, default=list).encode())
    for a in (spacing, mn, observed):
        h.update(np.ascontiguousarray(a, dtype=np.float64).tobytes())
    return h.hexdigest()[:16]


def invert_station(processed: ProcessedDataset, config: InversionConfig | None = None,
                   backend: InversionBackend | None = None) -> InversionResult:
    cfg = config or InversionConfig()
    backend = backend or PygimliBackend()
    if processed.lineage.get("array") != "schlumberger":
        raise InversionError("1D inversion is currently supported for Schlumberger data only.")
    if cfg.n_layers < 2:
        raise InversionError("n_layers must be at least 2.")
    t = processed.table
    use = t[(t.qc_status != "ERROR") & np.isfinite(t.apparent_resistivity) & (t.apparent_resistivity > 0)]
    if len(use) < 2 * cfg.n_layers - 1:
        raise InversionError(
            f"{len(use)} usable measurements is fewer than the {2 * cfg.n_layers - 1} "
            f"model parameters of a {cfg.n_layers}-layer model.")
    use = use.sort_values("ab_half_m")
    spacing = use.ab_half_m.to_numpy(float)
    mn = use.mn_half_m.to_numpy(float)
    obs = use.apparent_resistivity.to_numpy(float)

    raw = backend.invert(spacing, mn, obs, cfg)
    rho = np.clip(np.asarray(raw["resistivity"], float), *cfg.rho_bounds)
    th = np.asarray(raw["thickness"], float)
    resp = np.asarray(raw["response"], float)
    rel = (obs - resp) / obs
    rms = float(np.sqrt(np.mean(rel**2)) * 100)
    chi2 = float(np.mean((rel / (cfg.error_percent / 100.0)) ** 2))
    bottoms = np.append(np.cumsum(th), np.inf)
    tops = np.concatenate([[0.0], np.cumsum(th)])
    run_id = _run_id(spacing, mn, obs, cfg, processed.lineage["array"])
    return InversionResult(
        run_id=run_id, config=cfg, resistivity=rho, thickness=th, depth_top=tops,
        depth_bottom=bottoms, spacing=spacing, observed=obs, model_response=resp,
        rms_percent=rms, chi2=chi2, iterations=int(raw["iterations"]),
        converged=chi2 <= 1.0,
        metadata={"engine_version": ENGINE_VERSION, **raw["backend"],
                  "n_data": int(len(obs)), "rows_used": use.source_row.tolist()},
    )


class InversionHistory:
    """Append-only: a new run never replaces an earlier one."""
    def __init__(self):
        self._runs: list[InversionResult] = []

    def add(self, r: InversionResult) -> int:
        self._runs.append(r)
        return len(self._runs)

    def __len__(self):
        return len(self._runs)

    def __getitem__(self, i):
        return self._runs[i]

    def compare(self, i: int, j: int) -> pd.DataFrame:
        a, b = self._runs[i], self._runs[j]
        return pd.DataFrame({"metric": ["rms_percent", "chi2", "n_layers", "iterations"],
                             "a": [a.rms_percent, a.chi2, a.config.n_layers, a.iterations],
                             "b": [b.rms_percent, b.chi2, b.config.n_layers, b.iterations]})
