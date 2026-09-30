# Electrode array equations

Common basis (point current source on a homogeneous half-space, potential V = Iρ / 2πr):

    ρa = K · ΔV / I,    K = 2π / (1/AM − 1/BM − 1/AN + 1/BN)

K is stored as a positive magnitude. Remote electrodes are at ±∞ (their 1/r term is 0).
Positions below are along one line, lengths in metres.

| Array | Inputs | Electrode positions | K (closed form) |
|---|---|---|---|
| Schlumberger | L = AB/2, l = MN/2 | A=−L, M=−l, N=+l, B=+L | π (L² − l²) / (2 l) |
| Wenner | a | A=−1.5a, M=−0.5a, N=0.5a, B=1.5a | 2π a |
| Dipole-dipole | a, n | A=0, B=a, M=(n+1)a, N=(n+2)a | π n (n+1)(n+2) a |
| Pole-dipole (forward) | a, n | A=0, M=na, N=(n+1)a, B=∞ | 2π n (n+1) a |
| Pole-pole | a | A=0, M=a, B=N=∞ | 2π a |
| Gradient | AB, MN, x | A=−AB/2, B=AB/2, M/N = x ∓ MN/2 | general formula |

## Verification status (v0.1.0)
1. Closed forms above are hand-derived from the general formula and asserted in `tests/test_arrays.py`.
2. Closed form vs. general formula: agree to relative 1e-9 for every array.
3. Homogeneous half-space benchmark: potentials from the analytic point-source solution, recovered ρa = ρ to 1e-8.

4. **pyGIMLi cross-check (done):** `ert.geometricFactors` agrees with every array to relative 1e-9
   (`tests/test_pygimli_crosscheck.py`). Layered Schlumberger forward model (numerical Hankel integration,
   `app/inversion/forward.py`) agrees with `pygimli.physics.ves.VESModelling` to relative 1e-4 for a 3-layer
   model, plus analytic limits (half-space, rho1/rho2 asymptotes).

**Still not done:** comparison against published worked examples with page-level citations, and a
second independent package (e.g. ResIPy). pyGIMLi needs Python 3.12 and, on macOS, `brew install lapack`
with `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/opt/lapack/lib`.

## Guideline thresholds (WARNING only, not errors)
- Schlumberger: MN ≤ AB/5 (practical rule of thumb).
- Gradient: MN centre inside the middle third of AB.
- Dipole/pole-dipole: n > 8 flagged as low-signal.
- Adjacent-spacing ρa ratio > 3 flagged as abrupt change (configurable constant `JUMP_FACTOR`).
