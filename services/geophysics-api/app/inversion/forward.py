"""1D layered-earth forward model for the Schlumberger array (point-electrode limit).

rho_a(L) = rho_1 + L^2 * Int_0^inf [T(l) - rho_1] J1(l L) l dl
with the Pekeris/Koefoed resistivity-transform recursion for T (Koefoed 1979).
Direct numerical (adaptive) Hankel integration: slower than digital filters but
has no tabulated coefficients to mis-transcribe. Independent cross-check: pyGIMLi.
"""
import numpy as np
from scipy.integrate import quad
from scipy.special import j0, j1


def resistivity_transform(lam, rho, thick):
    """T(lambda) for layers rho[0..n-1], thick[0..n-2] (last layer is a half-space)."""
    t = float(rho[-1])
    for i in range(len(rho) - 2, -1, -1):
        th = np.tanh(lam * thick[i])
        t = (t + rho[i] * th) / (1.0 + t * th / rho[i])
    return t


def schlumberger_forward(ab_half, rho, thick):
    rho = np.asarray(rho, float)
    thick = np.asarray(thick, float)
    if len(thick) != len(rho) - 1:
        raise ValueError("Need n resistivities and n-1 thicknesses.")
    if np.any(rho <= 0) or np.any(thick <= 0):
        raise ValueError("Resistivities and thicknesses must be positive.")
    out = []
    for L in np.atleast_1d(np.asarray(ab_half, float)):
        if len(rho) == 1:
            out.append(rho[0])
            continue
        f = lambda lam: (resistivity_transform(lam, rho, thick) - rho[0]) * j1(lam * L) * lam
        # integrand decays like exp(-2 lam h1); integrate over intervals of one Bessel period
        upper = 40.0 / (2.0 * thick[0])
        edges = np.arange(0.0, upper + np.pi / L, np.pi / L)
        total = sum(quad(f, a, b, limit=100, epsabs=1e-12, epsrel=1e-10)[0]
                    for a, b in zip(edges[:-1], edges[1:]))
        out.append(rho[0] + L**2 * total)
    return np.array(out)


def _g(r, rho, thick):
    """Potential kernel g(r) = V(r) * 2*pi / I for a point source on a layered earth.
    g(r) = rho_1 / r + Int_0^inf [T(l) - rho_1] J0(l r) dl   (g = 0 for r = inf)."""
    if np.isinf(r):
        return 0.0
    if len(rho) == 1:
        return rho[0] / r
    f = lambda lam: (resistivity_transform(lam, rho, thick) - rho[0]) * j0(lam * r)
    upper = 40.0 / (2.0 * thick[0])
    edges = np.arange(0.0, upper + np.pi / r, np.pi / r)
    total = sum(quad(f, a, b, limit=100, epsabs=1e-12, epsrel=1e-10)[0]
                for a, b in zip(edges[:-1], edges[1:]))
    return rho[0] / r + total


def layered_apparent_resistivity(a, b, m, n, rho, thick):
    """Apparent resistivity for arbitrary collinear electrodes (arrays of positions, +inf = remote)
    over a layered earth: rho_a = K * dV / I with dV from the layered point-source potential."""
    rho = np.asarray(rho, float)
    thick = np.asarray(thick, float)
    if len(thick) != len(rho) - 1:
        raise ValueError("Need n resistivities and n-1 thicknesses.")
    if np.any(rho <= 0) or np.any(thick <= 0):
        raise ValueError("Resistivities and thicknesses must be positive.")
    a, b, m, n = (np.atleast_1d(np.asarray(x, float)) for x in (a, b, m, n))
    out = []
    for A, B, M, N in zip(*np.broadcast_arrays(a, b, m, n)):
        d = lambda p, q: np.inf if (np.isinf(p) or np.isinf(q)) else abs(p - q)
        am, bm, an, bn = d(A, M), d(B, M), d(A, N), d(B, N)
        inv = lambda r: 0.0 if np.isinf(r) else 1.0 / r
        den = inv(am) - inv(bm) - inv(an) + inv(bn)
        num = _g(am, rho, thick) - _g(bm, rho, thick) - _g(an, rho, thick) + _g(bn, rho, thick)
        out.append(num / den)
    return np.array(out)
