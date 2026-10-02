"""Equivalence analysis: which layered models fit the data about as well as the best one?

VES inversion is non-unique. This samples the parameter space around the best model (adaptive random walk in
log-parameters, bounded by the inversion bounds) and keeps every model whose misfit is statistically
indistinguishable from the best, using the usual nonlinear-least-squares confidence region

    SSR <= SSR_best * (1 + p / (N - p) * F(0.95; p, N - p))

with p = 2n - 1 parameters and N working-curve points. The returned min/max per layer are the range spanned by
those models, not a probability interval. If N <= p the data cannot constrain the model at all and no ranges
are reported. Averaged or smoothed working-curve points are not independent, so the region is, if anything,
slightly too tight.
"""
import numpy as np
from scipy.stats import f as f_dist

from .types import InversionConfig


def confidence_factor(n_data: int, n_layers: int, level: float = 0.95) -> float | None:
    p = 2 * n_layers - 1
    return None if n_data <= p else 1.0 + p / (n_data - p) * float(f_dist.ppf(level, p, n_data - p))


def equivalent_models(forward, obs, weights, thickness, resistivity, cfg: InversionConfig, n_eff: int,
                      n_samples: int, seed: int = 0) -> dict:
    """`forward(thickness, resistivity) -> response` at the data configurations; `weights` scale the residuals."""
    n = cfg.n_layers
    obs, w = np.asarray(obs, float), np.asarray(weights, float)

    def ssr(th, rho):
        r = np.asarray(forward(th, rho), float)
        v = float(np.sum(((obs - r) / obs / w) ** 2))
        return v if np.isfinite(v) else np.inf

    best = np.log(np.r_[thickness, resistivity])
    best_ssr = ssr(thickness, resistivity)
    factor = confidence_factor(n_eff, n, 0.95)
    out = {"method": "adaptive random walk; accepted if SSR <= SSR_best * (1 + p/(N-p) * F95)",
           "n_params": 2 * n - 1, "n_points": int(n_eff), "n_samples": int(n_samples), "confidence": 0.95}
    if factor is None or not np.isfinite(best_ssr) or best_ssr <= 0:
        return {**out, "constrained": False, "n_accepted": 0, "layers": [],
                "note": f"{n_eff} points cannot constrain {2 * n - 1} parameters; add data or use fewer layers."}

    limit = best_ssr * factor
    lo = np.log(np.r_[[cfg.thickness_bounds[0]] * (n - 1), [cfg.rho_bounds[0]] * n])
    hi = np.log(np.r_[[cfg.thickness_bounds[1]] * (n - 1), [cfg.rho_bounds[1]] * n])
    rng = np.random.default_rng(seed)
    pool = [best]
    for _ in range(n_samples):
        base = pool[rng.integers(len(pool))]
        step = rng.choice([0.05, 0.15, 0.4, 1.0])
        mask = rng.random(len(best)) < 0.5
        if not mask.any():
            mask[rng.integers(len(best))] = True
        cand = np.clip(base + mask * rng.normal(0.0, step, len(best)), lo, hi)
        m = np.exp(cand)
        if ssr(m[: n - 1], m[n - 1:]) <= limit:
            pool.append(cand)
    P = np.exp(np.array(pool))
    th, rho = P[:, : n - 1], P[:, n - 1:]
    top = np.hstack([np.zeros((len(P), 1)), np.cumsum(th, axis=1)])           # n tops
    layers = []
    for i in range(n):
        last = i == n - 1
        layers.append({
            "rho_min": float(rho[:, i].min()), "rho_max": float(rho[:, i].max()),
            "thickness_min": None if last else float(th[:, i].min()),
            "thickness_max": None if last else float(th[:, i].max()),
            "top_min": float(top[:, i].min()), "top_max": float(top[:, i].max()),
            "rho_at_bound": bool(rho[:, i].min() <= cfg.rho_bounds[0] * 1.001 or rho[:, i].max() >= cfg.rho_bounds[1] * 0.999),
        })
    return {**out, "constrained": True, "n_accepted": len(pool), "ssr_factor": float(factor),
            "misfit_limit_rms_percent": float(np.sqrt(limit / len(obs)) * 100),
            "layers": layers, "basement_depth_min": layers[-1]["top_min"], "basement_depth_max": layers[-1]["top_max"]}
