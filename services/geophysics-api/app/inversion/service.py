"""Inversion service: engine-owned abstraction over backends + immutable run history."""
import hashlib
import json
from dataclasses import asdict

import numpy as np
import pandas as pd

from app import ENGINE_VERSION
from app.arrays import get_array
from app.processing import ProcessedDataset
from .pygimli_backend import PygimliBackend
from .types import InversionBackend, InversionConfig, InversionResult


class InversionError(ValueError):
    pass


def _run_id(dist, observed, cfg, array) -> str:
    h = hashlib.sha256()
    h.update(json.dumps({"cfg": asdict(cfg), "array": array, "engine": ENGINE_VERSION},
                        sort_keys=True, default=list).encode())
    for a in (*[dist[k] for k in sorted(dist)], observed):
        h.update(np.ascontiguousarray(a, dtype=np.float64).tobytes())
    return h.hexdigest()[:16]


def _warnings(array: str) -> tuple[str, ...]:
    w = ["A good fit does not prove the geological model: VES inversion is non-unique "
         "(equivalence) and has limited resolution."]
    if array not in ("schlumberger", "wenner"):
        w.append(f"{array.replace('_', '-')} data are normally used for lateral profiling; a 1D "
                 "inversion assumes laterally homogeneous layers beneath this one location.")
    return tuple(w)


def invert_station(processed: ProcessedDataset, config: InversionConfig | None = None,
                   backend: InversionBackend | None = None) -> InversionResult:
    cfg = config or InversionConfig()
    backend = backend or PygimliBackend()
    array = processed.lineage.get("array")
    if array is None or processed.table.empty:
        raise InversionError("No processed data to invert.")
    arr = get_array(array)
    if cfg.n_layers < 2:
        raise InversionError("n_layers must be at least 2.")
    t = processed.table
    use = t[~t.qc_status.isin(["ERROR", "EXCLUDED"]) & np.isfinite(t.apparent_resistivity)
            & (t.apparent_resistivity > 0)]
    if len(use) < 2 * cfg.n_layers - 1:
        raise InversionError(
            f"{len(use)} usable measurements is fewer than the {2 * cfg.n_layers - 1} "
            f"model parameters of a {cfg.n_layers}-layer model.")
    params = {f: use[f"{f}_m"].to_numpy(float) for f in arr.required_fields}
    params.update({f: use[f].to_numpy(float) for f in arr.integer_fields})
    spacing_all = np.asarray(arr.spacing(**params), float)
    order = np.argsort(spacing_all, kind="stable")
    params = {k: v[order] for k, v in params.items()}
    use = use.iloc[order]
    spacing = spacing_all[order]
    a_, b_, m_, n_ = (np.asarray(x, float) for x in arr.electrodes(**params))
    d = lambda p, q: np.where(np.isinf(p) | np.isinf(q), np.inf, np.abs(p - q))
    with np.errstate(invalid="ignore"):   # inf - inf for remote electrodes is masked above
        dist = {"am": d(a_, m_), "an": d(a_, n_), "bm": d(b_, m_), "bn": d(b_, n_)}
    obs = use.apparent_resistivity.to_numpy(float)

    raw = backend.invert(spacing, dist, obs, cfg)
    rho = np.clip(np.asarray(raw["resistivity"], float), *cfg.rho_bounds)
    th = np.asarray(raw["thickness"], float)
    resp = np.asarray(raw["response"], float)
    rel = (obs - resp) / obs
    rms = float(np.sqrt(np.mean(rel**2)) * 100)
    chi2 = float(np.mean((rel / (cfg.error_percent / 100.0)) ** 2))
    bottoms = np.append(np.cumsum(th), np.inf)
    tops = np.concatenate([[0.0], np.cumsum(th)])
    run_id = _run_id(dist, obs, cfg, array)
    return InversionResult(
        run_id=run_id, config=cfg, resistivity=rho, thickness=th, depth_top=tops,
        depth_bottom=bottoms, spacing=spacing, observed=obs, model_response=resp,
        rms_percent=rms, chi2=chi2, iterations=int(raw["iterations"]),
        converged=chi2 <= 1.0,
        warnings=_warnings(array),
        metadata={"engine_version": ENGINE_VERSION, "array": array, **raw["backend"],
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
