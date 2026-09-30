"""Scientific validation of geometric factors and apparent resistivity.

Three independent checks per array:
 1. Hand-computed reference values from the published closed forms.
 2. Closed form vs. the general four-electrode formula (independent code path).
 3. Homogeneous half-space benchmark: potentials are computed from the point-source
    solution V = I*rho/(2*pi*r); recovered rho_a must equal rho.
Tolerance: relative 1e-9 (pure floating point arithmetic, no measurement noise).
"""
import numpy as np
import pytest

from app.arrays import REGISTRY, general_geometric_factor, get_array

RTOL = 1e-9

CASES = {
    "schlumberger": dict(ab_half=[10.0, 50.0, 200.0], mn_half=[1.0, 5.0, 10.0]),
    "wenner": dict(a=[1.0, 10.0, 32.5]),
    "dipole_dipole": dict(a=[5.0, 10.0, 10.0], n=[1, 2, 6]),
    "pole_dipole": dict(a=[5.0, 10.0, 10.0], n=[1, 3, 6]),
    "pole_pole": dict(a=[1.0, 10.0, 50.0]),
    "gradient": dict(ab=[100.0, 200.0, 200.0], mn=[5.0, 10.0, 10.0], x=[0.0, 20.0, -25.0]),
}


def test_reference_values():
    # Hand-computed from the published closed forms.
    assert get_array("wenner").geometric_factor(a=10.0) == pytest.approx(62.83185307, rel=1e-8)
    assert get_array("schlumberger").geometric_factor(ab_half=10.0, mn_half=1.0) == \
        pytest.approx(np.pi * 99 / 2, rel=RTOL)                       # 155.5088
    assert get_array("dipole_dipole").geometric_factor(a=10.0, n=1) == \
        pytest.approx(np.pi * 1 * 2 * 3 * 10, rel=RTOL)               # 188.4956
    assert get_array("pole_dipole").geometric_factor(a=10.0, n=2) == \
        pytest.approx(2 * np.pi * 2 * 3 * 10, rel=RTOL)               # 376.9911
    assert get_array("pole_pole").geometric_factor(a=10.0) == pytest.approx(62.83185307, rel=1e-8)


@pytest.mark.parametrize("name", list(CASES))
def test_closed_form_matches_general_formula(name):
    arr, p = get_array(name), {k: np.array(v, float) for k, v in CASES[name].items()}
    np.testing.assert_allclose(arr.closed_form_k(**p),
                               general_geometric_factor(*arr.electrodes(**p)), rtol=RTOL)


def _potential(r_src, x, current):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(np.isinf(x) | np.isinf(r_src), 0.0,
                        current / (2 * np.pi * np.abs(x - r_src)))


@pytest.mark.parametrize("name", list(CASES))
@pytest.mark.parametrize("rho", [1.0, 47.3, 1e4])
def test_homogeneous_half_space_recovers_rho(name, rho):
    arr, p = get_array(name), {k: np.array(v, float) for k, v in CASES[name].items()}
    a, b, m, n = arr.electrodes(**p)
    current = 0.25
    # potential at M and N from +I at A and -I at B (rho scales V linearly)
    v = lambda x: rho * (_potential(a, x, current) - _potential(b, x, current))
    dv = np.abs(v(m) - v(n))
    rho_a = arr.apparent_resistivity(dv / current, **p)
    np.testing.assert_allclose(rho_a, rho, rtol=1e-8)


def test_all_six_arrays_registered():
    assert set(REGISTRY) == set(CASES)


def test_degenerate_geometry_raises():
    with pytest.raises(ValueError):
        general_geometric_factor(0, 10, 5, 5)


def test_unknown_array():
    with pytest.raises(ValueError, match="Unknown array"):
        get_array("nope")
