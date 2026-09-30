from dataclasses import dataclass, field
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class InversionConfig:
    """All parameters that influence a result. Hashed into the run id (reproducibility)."""
    n_layers: int = 3
    error_percent: float = 3.0            # assumed relative data error
    lam: float = 10.0                     # regularisation strength
    max_iter: int = 30
    rho_bounds: tuple[float, float] = (0.1, 1e5)      # ohm-m
    thickness_bounds: tuple[float, float] = (0.1, 1e3)  # m
    start_rho: tuple[float, ...] | None = None        # length n_layers, else data median
    start_thickness: tuple[float, ...] | None = None  # length n_layers-1, else log-spaced


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
    converged: bool                   # chi2 <= 1 reached within max_iter
    metadata: dict = field(default_factory=dict)
    warnings: tuple[str, ...] = (
        "A good fit does not prove the geological model: VES inversion is non-unique "
        "(equivalence) and has limited resolution.",
    )


class InversionBackend(Protocol):
    def invert(self, spacing, distances: dict, observed, config: InversionConfig) -> dict: ...
