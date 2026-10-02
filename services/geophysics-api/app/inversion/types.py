import os
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from app.processing.working_curve import WorkingCurveConfig


@dataclass(frozen=True)
class InversionConfig:
    """All parameters that influence a result. Hashed into the run id (reproducibility)."""
    n_layers: int = 3
    error_percent: float = 3.0            # assumed relative data error
    lam: float = 10.0                     # regularisation strength
    max_iter: int = 30
    n_starts: int = 6                     # starting models tried (1 = single start from the default/user model)
    equivalence_samples: int = field(                      # models sampled for the equivalence analysis (0 = skip)
        default_factory=lambda: int(os.environ.get("VES_EQUIVALENCE_SAMPLES", 3000)))
    lam_ratios: tuple[float, ...] = (1.0, 0.1)   # regularisation strengths tried, as multiples of `lam`
    rho_bounds: tuple[float, float] = (0.1, 1e5)      # ohm-m
    thickness_bounds: tuple[float, float] = (0.1, 1e3)  # m
    start_rho: tuple[float, ...] | None = None        # length n_layers, else data median
    start_thickness: tuple[float, ...] | None = None  # length n_layers-1, else log-spaced
    working: WorkingCurveConfig = field(default_factory=WorkingCurveConfig)   # data preparation (recorded)


@dataclass
class InversionResult:
    run_id: str
    config: InversionConfig
    resistivity: np.ndarray           # ohm-m, len n
    thickness: np.ndarray             # m, len n-1 (last layer is a half-space)
    depth_top: np.ndarray             # m, len n
    depth_bottom: np.ndarray          # m, len n (last = inf)
    spacing: np.ndarray               # AB/2 (m) of the data
    observed: np.ndarray              # ohm-m
    model_response: np.ndarray        # ohm-m
    rms_percent: float                # sqrt(mean(((obs-model)/obs)^2)) * 100
    chi2: float                       # error-weighted misfit; ~1 when fit matches assumed error
    iterations: int
    converged: bool                   # the optimiser finished (stopped before max_iter) for the reported run
    fit_within_error: bool = False    # chi2 <= 1: the data are fitted to within the assumed error
    metadata: dict = field(default_factory=dict)
    warnings: tuple[str, ...] = (
        "A good fit does not prove the geological model: VES inversion is non-unique "
        "(equivalence) and has limited resolution.",
    )
    raw_spacing: np.ndarray = field(default_factory=lambda: np.array([]))    # usable raw points
    raw_observed: np.ndarray = field(default_factory=lambda: np.array([]))
    rms_raw_percent: float | None = None     # misfit of the model against the RAW data
    equivalence: dict = field(default_factory=dict)   # range of models that fit as well as the best (empty if skipped)
    working: dict = field(default_factory=dict)   # shifts, segments, description (empty when raw data were fitted)


class InversionBackend(Protocol):
    def invert(self, spacing, distances: dict, observed, config: InversionConfig, error_scale=None) -> dict: ...
    def forward_model(self, distances: dict, n_layers: int): ...
