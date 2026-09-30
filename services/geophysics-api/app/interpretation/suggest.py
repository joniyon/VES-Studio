"""Suggest POSSIBLE lithologies for an inverted layer. Suggestions are ranked candidates with the
basis stated - never a single answer and never a confidence claim. The interpretation itself
(lithology, confidence, notes) belongs to the user."""
import math
from dataclasses import dataclass

from .catalogue import CATALOGUE, Lithology


@dataclass(frozen=True)
class Suggestion:
    lithology: Lithology
    in_range: bool
    depth_ok: bool
    score: float          # lower = better fit (log10 distance + depth penalty)
    basis: str


def _log_dist(rho: float, lo: float, hi: float) -> float:
    if lo <= rho <= hi:
        return 0.0
    return abs(math.log10(rho) - math.log10(lo if rho < lo else hi))


def suggest(rho: float, depth_top: float, depth_bottom: float | None, max_n: int = 4) -> list[Suggestion]:
    if not (rho > 0) or not math.isfinite(rho):
        raise ValueError("Resistivity must be a positive, finite number.")
    out = []
    for l in CATALOGUE:
        if l.id == "unclassified":
            continue
        in_range = l.rho_min <= rho <= l.rho_max
        depth_ok = depth_top >= l.depth_min and (l.depth_max is None or depth_top <= l.depth_max)
        score = _log_dist(rho, l.rho_min, l.rho_max) + (0.0 if depth_ok else 0.5)
        if in_range:
            mid = 0.5 * (math.log10(l.rho_min) + math.log10(l.rho_max))
            score += 0.01 * abs(math.log10(rho) - mid)   # tie-break only, well inside one "in range" tier
        bottom = "∞" if depth_bottom is None else f"{depth_bottom:g}"
        basis = (f"ρ = {rho:.3g} Ωm is {'within' if in_range else 'outside'} the indicative range for "
                 f"{l.name.lower()} ({l.rho_min:g}–{l.rho_max:g} Ωm); layer depth {depth_top:g}–{bottom} m is "
                 f"{'consistent with' if depth_ok else 'unusual for'} this material.")
        out.append(Suggestion(l, in_range, depth_ok, score, basis))
    out.sort(key=lambda s: s.score)
    return out[:max_n]
