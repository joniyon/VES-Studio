"""Inversion service: engine-owned abstraction over backends + immutable run history."""
import hashlib
import json
from dataclasses import asdict

import numpy as np
import pandas as pd

from app import ENGINE_VERSION
from app.arrays import get_array
from app.processing import SOUNDING_ARRAYS, ProcessedDataset, WorkingCurveConfig, build_working_curve
from .forward import layered_apparent_resistivity
from .pygimli_backend import PygimliBackend
from .types import InversionBackend, InversionConfig, InversionResult


class InversionError(ValueError):
    pass


def _random_starts(spacing, obs, cfg: InversionConfig, n: int):
    """Deterministic (fixed seed) random starting models: log-uniform interface depths and resistivities."""
    rng = np.random.default_rng(0)
    lo_d, hi_d = spacing.min() / 2, spacing.max() / 2
    lo_r, hi_r = obs.min() / 2, obs.max() * 3
    for _ in range(n):
        depth = np.sort(np.exp(rng.uniform(np.log(lo_d), np.log(hi_d), cfg.n_layers - 1)))
        rho = np.clip(np.exp(rng.uniform(np.log(lo_r), np.log(hi_r), cfg.n_layers)), *cfg.rho_bounds)
        yield tuple(rho), tuple(np.maximum(np.diff(np.r_[0.0, depth]), cfg.thickness_bounds[0]))


def _solve(backend, spacing, dist, obs, cfg: InversionConfig, error_scale=None):
    """Best of several starting models x regularisation strengths (lowest weighted misfit).
    Returns (raw backend result, number of runs tried, number that failed)."""
    from dataclasses import replace
    w = np.ones(len(obs)) if error_scale is None else np.asarray(error_scale, float)
    starts = [(cfg.start_rho, cfg.start_thickness)] + list(_random_starts(spacing, obs, cfg, cfg.n_starts - 1))
    lams = [cfg.lam * r for r in cfg.lam_ratios] if cfg.n_starts > 1 else [cfg.lam]
    best, best_score, tried, failed = None, np.inf, 0, 0
    for lam in lams:
        for rho0, th0 in starts:
            tried += 1
            try:
                raw = backend.invert(spacing, dist, obs, replace(cfg, lam=lam, start_rho=rho0, start_thickness=th0),
                                     error_scale=error_scale)
                resp = np.asarray(raw["response"], float)
                score = float(np.sqrt(np.mean(((obs - resp) / obs / w) ** 2)))
            except Exception:
                failed += 1
                continue
            if np.isfinite(score) and score < best_score:
                best, best_score = {**raw, "lam": lam}, score
    if best is None:
        raise InversionError("The inversion failed for every starting model; check the data and settings.")
    return best, tried, failed


def _run_id(dist, observed, cfg, array) -> str:
    h = hashlib.sha256()
    h.update(json.dumps({"cfg": asdict(cfg), "array": array, "engine": ENGINE_VERSION},
                        sort_keys=True, default=list).encode())
    for a in (*[dist[k] for k in sorted(dist)], observed):
        h.update(np.ascontiguousarray(a, dtype=np.float64).tobytes())
    return h.hexdigest()[:16]


def _warnings(array: str, working: WorkingCurveConfig, rms_fit: float, rms_raw: float | None) -> tuple[str, ...]:
    w = ["A good fit does not prove the geological model: VES inversion is non-unique "
         "(equivalence) and has limited resolution."]
    if array not in ("schlumberger", "wenner"):
        w.append(f"{array.replace('_', '-')} data are normally used for lateral profiling; a 1D "
                 "inversion assumes laterally homogeneous layers beneath this one location.")
    if not working.is_identity:
        w.append(f"The model was fitted to a prepared working curve ({working.describe()}). Misfit: "
                 f"{rms_fit:.1f} % on the working curve, {rms_raw:.1f} % on the raw data. "
                 "Preparation can hide real structure; compare both curves.")
    return tuple(w)


def _usable(processed: ProcessedDataset, cfg: InversionConfig):
    if processed.table.empty or processed.lineage.get("array") is None:
        raise InversionError("No processed data to invert.")
    if cfg.n_layers < 2:
        raise InversionError("n_layers must be at least 2.")
    t = processed.table
    use = t[~t.qc_status.isin(["ERROR", "EXCLUDED"]) & np.isfinite(t.apparent_resistivity)
            & (t.apparent_resistivity > 0)]
    return get_array(processed.lineage["array"]), use.sort_values("source_row")   # file (measurement) order


def _geometry(arr, params):
    a_, b_, m_, n_ = (np.asarray(x, float) for x in arr.electrodes(**params))
    d = lambda p, q: np.where(np.isinf(p) | np.isinf(q), np.inf, np.abs(p - q))
    with np.errstate(invalid="ignore"):   # inf - inf for remote electrodes is masked above
        dist = {"am": d(a_, m_), "an": d(a_, n_), "bm": d(b_, m_), "bn": d(b_, n_)}
    return (a_, b_, m_, n_), dist


def _raw_params(arr, use):
    params = {f: use[f"{f}_m"].to_numpy(float) for f in arr.required_fields}
    params.update({f: use[f].to_numpy(float) for f in arr.integer_fields})
    return params


def prepare_working_curve(processed: ProcessedDataset, working: WorkingCurveConfig):
    """Working curve for a processed dataset (sounding arrays only). Used by the API preview and by inversion."""
    arr, use = _usable(processed, InversionConfig(working=working))
    if arr.name not in SOUNDING_ARRAYS:
        raise InversionError("Working-curve preparation is available for Schlumberger, Wenner and pole-pole "
                             "soundings only.")
    params = _raw_params(arr, use)
    spacing = np.asarray(arr.spacing(**params), float)
    mn = params.get("mn_half")
    return arr, use, spacing, mn, build_working_curve(spacing, use.apparent_resistivity.to_numpy(float), mn,
                                                      use.source_row.to_numpy(int), working)


def invert_station(processed: ProcessedDataset, config: InversionConfig | None = None,
                   backend: InversionBackend | None = None) -> InversionResult:
    cfg = config or InversionConfig()
    backend = backend or PygimliBackend()
    arr, use = _usable(processed, cfg)
    array = arr.name
    if len(use) < 2 * cfg.n_layers - 1:
        raise InversionError(
            f"{len(use)} usable measurements is fewer than the {2 * cfg.n_layers - 1} "
            f"model parameters of a {cfg.n_layers}-layer model.")
    raw_params = _raw_params(arr, use)
    raw_spacing = np.asarray(arr.spacing(**raw_params), float)
    raw_obs = use.apparent_resistivity.to_numpy(float)

    working_info: dict = {}
    if cfg.working.is_identity:
        order = np.argsort(raw_spacing, kind="stable")
        params = {k: v[order] for k, v in raw_params.items()}
        spacing, obs, rows_used = raw_spacing[order], raw_obs[order], use.source_row.to_numpy(int)[order]
    else:
        _, _, _, _, wc = prepare_working_curve(processed, cfg.working)
        if len(wc.spacing) < 2 * cfg.n_layers - 1:
            raise InversionError(f"The working curve has {len(wc.spacing)} points, fewer than the "
                                 f"{2 * cfg.n_layers - 1} parameters of a {cfg.n_layers}-layer model.")
        spacing, obs = wc.spacing, wc.values
        rows_used = np.array(sorted({r for g in wc.source_rows for r in g}))
        working_info = {"description": cfg.working.describe(), "shifts": wc.shifts, "notes": wc.notes,
                        "n_segments": len(wc.shifts), "source_rows": wc.source_rows}
        # Each working point is evaluated at the real electrode configuration(s) behind it: one datum per
        # raw row (its own MN/2), all targeting the working value. No synthetic, averaged MN/2 is invented.
        # Points that merge k raw rows are down-weighted (error * sqrt(k)) so overlaps are not counted twice.
        row_pos = {int(r): i for i, r in enumerate(use.source_row.to_numpy(int))}
        expand = [[row_pos[r] for r in g] for g in wc.source_rows]
        idx = np.array([i for g in expand for i in g])
        group = np.repeat(np.arange(len(expand)), [len(g) for g in expand])
        k = np.array([len(g) for g in expand])[group]
        params = {key: np.asarray(v)[idx] for key, v in raw_params.items()}
        d_obs, d_err = obs[group], np.sqrt(k)

    _, dist = _geometry(arr, params)
    if cfg.working.is_identity:
        raw, tried, failed = _solve(backend, spacing, dist, obs, cfg)
        resp = np.asarray(raw["response"], float)
    else:
        raw, tried, failed = _solve(backend, raw_spacing[idx], dist, d_obs, cfg, error_scale=d_err)
        r_d = np.asarray(raw["response"], float)
        # response per working point = geometric mean over the raw configurations behind it
        resp = np.exp(np.bincount(group, np.log(r_d)) / np.bincount(group))
    rho = np.clip(np.asarray(raw["resistivity"], float), *cfg.rho_bounds)
    th = np.asarray(raw["thickness"], float)
    rel = (obs - resp) / obs
    rms = float(np.sqrt(np.mean(rel**2)) * 100)
    chi2 = float(np.mean((rel / (cfg.error_percent / 100.0)) ** 2))

    if cfg.working.is_identity:
        rms_raw = rms
    else:   # misfit of the same model against the raw readings, via the independent layered forward model
        ra = arr.electrodes(**raw_params)
        rel_raw = (raw_obs - layered_apparent_resistivity(*ra, rho, th)) / raw_obs
        rms_raw = float(np.sqrt(np.mean(rel_raw**2)) * 100)

    bottoms = np.append(np.cumsum(th), np.inf)
    tops = np.concatenate([[0.0], np.cumsum(th)])
    return InversionResult(
        run_id=_run_id(dist, obs, cfg, array), config=cfg, resistivity=rho, thickness=th, depth_top=tops,
        depth_bottom=bottoms, spacing=spacing, observed=obs, model_response=resp,
        rms_percent=rms, chi2=chi2, iterations=int(raw["iterations"]),
        converged=int(raw["iterations"]) < cfg.max_iter, fit_within_error=chi2 <= 1.0,
        warnings=_warnings(array, cfg.working, rms, rms_raw),
        metadata={"engine_version": ENGINE_VERSION, "array": array, **raw["backend"],
                  "lam_used": float(raw["lam"]), "starts_tried": tried, "starts_failed": failed,
                  "n_data": int(len(obs)), "n_raw": int(len(raw_obs)), "rows_used": [int(r) for r in rows_used]},
        raw_spacing=raw_spacing, raw_observed=raw_obs, rms_raw_percent=rms_raw, working=working_info,
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
