"""Base class for electrode arrays.

Conventions (all lengths in metres, positions along a single survey line):
  A, B  current electrodes (A is the +I electrode)
  M, N  potential electrodes, measured potential is V_M - V_N
  A remote ("infinite") electrode is represented by +inf.

Point-source potential over a homogeneous half-space:
  V(r) = I * rho / (2 * pi * r)
so   dV = I * rho / (2*pi) * (1/AM - 1/BM - 1/AN + 1/BN)
and  rho_a = K * dV / I,   K = 2*pi / (1/AM - 1/BM - 1/AN + 1/BN)

K is reported as a positive magnitude; the sign of dV depends on electrode
ordering convention and is normalised so that a positive resistance yields a
positive apparent resistivity. (Telford et al. 1990; Koefoed 1979; Loke 2004.)
"""
from abc import ABC, abstractmethod

import numpy as np

from app.quality.issues import Issue, Severity


def general_geometric_factor(a, b, m, n):
    """Geometric factor magnitude for arbitrary collinear electrode positions."""
    a, b, m, n = (np.asarray(x, dtype=float) for x in (a, b, m, n))
    with np.errstate(divide="ignore", invalid="ignore"):
        inv = lambda p, q: np.where(np.isinf(p) | np.isinf(q), 0.0, 1.0 / np.abs(p - q))
        s = inv(a, m) - inv(b, m) - inv(a, n) + inv(b, n)
    if np.any(s == 0):
        raise ValueError("Degenerate electrode geometry: geometric factor is infinite.")
    return np.abs(2.0 * np.pi / s)


class ElectrodeArray(ABC):
    name: str
    required_fields: tuple[str, ...]      # names of distance-like columns
    integer_fields: tuple[str, ...] = ()  # dimensionless columns (e.g. n)
    references: tuple[str, ...] = ()

    @abstractmethod
    def electrodes(self, **p):
        """Return (A, B, M, N) positions in metres. Values may be numpy arrays."""

    @abstractmethod
    def closed_form_k(self, **p):
        """Published closed-form geometric factor."""

    def geometric_factor(self, **p):
        return self.closed_form_k(**p)

    def validate_row(self, row: dict, index: int | None = None) -> list[Issue]:
        """Array-specific geometry checks for one row (SI units)."""
        return []

    def apparent_resistivity(self, resistance, **p):
        return self.geometric_factor(**p) * np.asarray(resistance, dtype=float)

    def spacing(self, **p):
        """Characteristic spacing for plotting apparent resistivity curves."""
        raise NotImplementedError

    def _require_positive(self, row, index, *names):
        out = []
        for f in names:
            v = row.get(f)
            if v is None or not np.isfinite(v) or v <= 0:
                out.append(Issue(Severity.ERROR, "GEOM_NONPOSITIVE",
                                 f"{f} must be a positive number.", index, f))
        return out
