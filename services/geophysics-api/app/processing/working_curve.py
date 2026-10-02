"""Working curve: an explicit, recorded preparation step between QC and inversion.

Raw measurements are never modified. From the usable raw points we derive a *working curve*:
  1. Segment matching ("shift"): a sounding is measured in segments; MN is widened between them and the
     last spacing of one segment is repeated as the first of the next. Lateral inhomogeneity near the
     potential electrodes can offset a whole segment, so each segment is multiplied by one factor so the
     repeated spacings agree with the neighbouring segment (anchor segment = 1.0). This is standard
     practice in manual VES interpretation.
  2. Overlap merging ("average" / after "shift"): repeated spacings become one point (geometric mean).
  3. Smoothing across neighbouring spacings in log10(rho_a): running median (robust to single spikes)
     or a Hanning-weighted mean. Windows shrink at the ends of the curve.
Interpreting smoothed data can hide real structure; the choice is always shown and reported, and the
misfit against the raw data is reported next to the misfit against the working curve.
Applies to single-spacing sounding arrays only (Schlumberger, Wenner, pole-pole).
"""
from dataclasses import dataclass, field

import numpy as np

OVERLAP_MODES = ("none", "average", "shift")
SMOOTH_MODES = ("none", "median", "hanning")
SOUNDING_ARRAYS = ("schlumberger", "wenner", "pole_pole")


@dataclass(frozen=True)
class WorkingCurveConfig:
    overlap: str = "none"        # none | average | shift
    anchor_segment: int = 0      # segment left unshifted (shift mode), zero-based
    smooth: str = "none"         # none | median | hanning
    window: int = 3              # 3 or 5

    def __post_init__(self):
        if self.overlap not in OVERLAP_MODES:
            raise ValueError(f"overlap must be one of {OVERLAP_MODES}.")
        if self.smooth not in SMOOTH_MODES:
            raise ValueError(f"smooth must be one of {SMOOTH_MODES}.")
        if self.window not in (3, 5):
            raise ValueError("window must be 3 or 5.")
        if self.anchor_segment < 0:
            raise ValueError("anchor_segment must be >= 0.")

    @property
    def is_identity(self) -> bool:
        return self.overlap == "none" and self.smooth == "none"

    def describe(self) -> str:
        if self.is_identity:
            return "raw data (no shifting, merging or smoothing)"
        parts = []
        if self.overlap == "shift":
            parts.append(f"segments shifted to match at overlaps (anchor: segment {self.anchor_segment + 1}), overlaps averaged")
        elif self.overlap == "average":
            parts.append("repeated spacings averaged (geometric mean)")
        if self.smooth != "none":
            parts.append(f"{self.smooth} smoothing over {self.window} neighbouring spacings (log scale)")
        return "; ".join(parts)


@dataclass
class WorkingCurve:
    spacing: np.ndarray
    values: np.ndarray
    source_rows: list[list[int]]          # raw row indices behind each working point
    segments: np.ndarray                   # segment id of each raw point (input order)
    shifts: list[float]                    # multiplicative factor per segment (1.0 = unshifted)
    notes: list[str] = field(default_factory=list)


def segment_ids(spacing: np.ndarray) -> np.ndarray:
    """A new segment starts wherever a spacing repeats (MN change). Requires non-decreasing order."""
    seg = np.zeros(len(spacing), int)
    for i in range(1, len(spacing)):
        if spacing[i] < spacing[i - 1]:
            raise ValueError("Segment matching needs rows in measurement order with non-decreasing spacing "
                             f"(row {i} goes back from {spacing[i - 1]:g} to {spacing[i]:g}).")
        seg[i] = seg[i - 1] + (1 if spacing[i] == spacing[i - 1] else 0)
    return seg


def _smooth(logv: np.ndarray, mode: str, window: int) -> np.ndarray:
    if mode == "none" or len(logv) < 3:
        return logv.copy()
    h = window // 2
    kernel = {3: np.array([1.0, 2.0, 1.0]), 5: np.array([1.0, 4.0, 6.0, 4.0, 1.0])}[window]
    out = np.empty_like(logv)
    for i in range(len(logv)):
        lo, hi = max(0, i - h), min(len(logv), i + h + 1)
        if mode == "median":
            out[i] = np.median(logv[lo:hi])
        else:
            w = kernel[lo - (i - h): hi - (i - h)]
            out[i] = np.sum(w * logv[lo:hi]) / np.sum(w)
    return out


def build_working_curve(spacing, values, rows=None, cfg: WorkingCurveConfig | None = None) -> WorkingCurve:
    """spacing/values in measurement order; `rows` = raw row ids for lineage. MN/2 is deliberately not carried:
    the inversion evaluates each working point at the real MN/2 of the raw rows behind it (`source_rows`)."""
    cfg = cfg or WorkingCurveConfig()
    sp = np.asarray(spacing, float)
    v = np.asarray(values, float)
    if np.any(v <= 0) or np.any(~np.isfinite(v)):
        raise ValueError("Working curve needs positive, finite apparent resistivities.")
    n = len(sp)
    rows_a = list(range(n)) if rows is None else list(map(int, rows))
    notes: list[str] = []

    seg = segment_ids(sp) if cfg.overlap == "shift" else np.zeros(n, int)
    shifts = [1.0] * (int(seg.max()) + 1 if n else 1)
    logv = np.log(v)

    if cfg.overlap == "shift":
        K = len(shifts)
        if cfg.anchor_segment >= K:
            raise ValueError(f"anchor_segment {cfg.anchor_segment + 1} does not exist; the data have {K} segment(s).")

        def seg_log_by_spacing(k):
            d: dict[float, list[float]] = {}
            for x, lv in zip(sp[seg == k], logv[seg == k]):
                d.setdefault(float(x), []).append(lv)
            return {x: float(np.mean(l)) for x, l in d.items()}

        def match(k, ref):
            a, b = seg_log_by_spacing(ref), seg_log_by_spacing(k)
            common = sorted(set(a) & set(b))
            if not common:
                notes.append(f"Segments {ref + 1} and {k + 1} share no spacing; segment {k + 1} was not shifted.")
                return 1.0
            return float(np.exp(np.mean([a[x] + np.log(shifts[ref]) - b[x] for x in common])))

        for k in range(cfg.anchor_segment + 1, K):
            shifts[k] = match(k, k - 1)
        for k in range(cfg.anchor_segment - 1, -1, -1):
            shifts[k] = match(k, k + 1)
        logv = logv + np.log(np.array(shifts))[seg]

    # merge repeated spacings (average / shift modes)
    if cfg.overlap in ("average", "shift"):
        uniq = np.unique(sp)
        w_sp, w_log, w_rows = [], [], []
        for x in uniq:
            idx = np.flatnonzero(sp == x)
            w_sp.append(x)
            w_log.append(float(np.mean(logv[idx])))
            w_rows.append([rows_a[i] for i in idx])
        w_sp, w_log = np.array(w_sp), np.array(w_log)
    else:
        order = np.argsort(sp, kind="stable")
        w_sp, w_log = sp[order], logv[order]
        w_rows = [[rows_a[i]] for i in order]

    w_log = _smooth(w_log, cfg.smooth, cfg.window)
    return WorkingCurve(spacing=w_sp, values=np.exp(w_log), source_rows=w_rows,
                        segments=seg, shifts=shifts, notes=notes)
