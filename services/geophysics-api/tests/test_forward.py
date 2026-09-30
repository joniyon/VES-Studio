"""Layered-earth forward model validation (analytic limits + pyGIMLi cross-check)."""
import numpy as np
import pytest

from app.inversion.forward import schlumberger_forward

AB = np.array([1.5, 3, 6, 12, 25, 50, 100, 200.0])


def test_single_layer_is_rho():
    np.testing.assert_allclose(schlumberger_forward(AB, [73.0], []), 73.0)


def test_two_layer_asymptotes():
    r = schlumberger_forward([0.1, 1e4], [100.0, 10.0], [5.0])
    assert r[0] == pytest.approx(100.0, rel=1e-3)     # AB/2 << h1 -> rho1
    assert r[1] == pytest.approx(10.0, rel=2e-2)      # AB/2 >> h1 -> rho2


def test_identical_layers_reduce_to_half_space():
    np.testing.assert_allclose(schlumberger_forward(AB, [50, 50, 50], [3, 7]), 50.0, rtol=1e-6)


def test_input_validation():
    with pytest.raises(ValueError):
        schlumberger_forward(AB, [1, 2], [])
    with pytest.raises(ValueError):
        schlumberger_forward(AB, [1, -2], [3])


def test_matches_pygimli_three_layer():
    pg = pytest.importorskip("pygimli")
    from pygimli.physics.ves import VESModelling
    rho, th = [100.0, 20.0, 300.0], [2.0, 10.0]
    ref = np.array(VESModelling(ab2=AB, mn2=np.full(len(AB), 1e-4)).response(pg.Vector(th + rho)))
    np.testing.assert_allclose(schlumberger_forward(AB, rho, th), ref, rtol=1e-4)
