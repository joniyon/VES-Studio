from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("pygimli")
from app.inversion import InversionConfig, InversionError, InversionHistory, invert_station
from app.processing import process_dataset

BENCH = Path(__file__).resolve().parents[3] / "scientific" / "benchmark-data"
TRUE_RHO, TRUE_TH = np.array([100.0, 20.0, 300.0]), np.array([2.0, 10.0])


@pytest.fixture(scope="module")
def clean():
    return process_dataset(pd.read_csv(BENCH / "synthetic_schlumberger_3layer.csv"), "schlumberger")


@pytest.fixture(scope="module")
def result(clean):
    return invert_station(clean, InversionConfig(n_layers=3, error_percent=2.0))


def test_recovers_synthetic_model(result):
    np.testing.assert_allclose(result.resistivity, TRUE_RHO, rtol=0.05)
    np.testing.assert_allclose(result.thickness, TRUE_TH, rtol=0.10)
    assert result.rms_percent < 1.0 and result.converged


def test_output_structure(result):
    assert result.depth_top.tolist() == [0.0, pytest.approx(result.thickness[0]),
                                         pytest.approx(result.thickness.sum())]
    assert np.isinf(result.depth_bottom[-1])
    assert len(result.model_response) == len(result.observed) == len(result.spacing)
    assert result.metadata["pygimli"] and result.metadata["engine_version"]
    assert "non-unique" in result.warnings[0]


def test_reproducible(clean, result):
    again = invert_station(clean, InversionConfig(n_layers=3, error_percent=2.0))
    assert again.run_id == result.run_id
    np.testing.assert_array_equal(again.resistivity, result.resistivity)
    np.testing.assert_array_equal(again.thickness, result.thickness)


def test_config_changes_run_id_and_history_is_append_only(clean, result):
    other = invert_station(clean, InversionConfig(n_layers=3, error_percent=5.0))
    assert other.run_id != result.run_id
    h = InversionHistory()
    h.add(result), h.add(other)
    assert len(h) == 2 and h[0] is result
    assert list(h.compare(0, 1).metric)[:2] == ["rms_percent", "chi2"]


def test_noisy_data_stays_reasonable(clean):
    rng = np.random.default_rng(42)
    df = pd.read_csv(BENCH / "synthetic_schlumberger_3layer.csv")
    df["resistance"] *= np.exp(rng.normal(0, 0.03, len(df)))
    res = invert_station(process_dataset(df, "schlumberger"), InversionConfig(n_layers=3, error_percent=3.0))
    assert np.isfinite(res.resistivity).all()
    assert res.rms_percent < 6.0
    np.testing.assert_allclose(res.resistivity[0], 100.0, rtol=0.25)


def test_model_response_agrees_with_engine_forward(result, clean):
    from app.inversion.forward import schlumberger_forward
    ours = schlumberger_forward(result.spacing, result.resistivity, result.thickness)
    # backend uses finite MN; engine forward is the point-electrode limit
    np.testing.assert_allclose(ours, result.model_response, rtol=0.03)


def _synthetic(array, rho=(100.0, 20.0, 300.0), th=(2.0, 10.0), **p):
    """Noise-free sounding for any array via the engine's independent layered forward model."""
    from app.arrays import get_array
    from app.inversion.forward import layered_apparent_resistivity
    arr = get_array(array)
    p = {k: np.asarray(v, float) for k, v in p.items()}
    ra = layered_apparent_resistivity(*arr.electrodes(**p), rho, th)
    df = pd.DataFrame({k: v for k, v in p.items()})
    df["resistance"] = ra / arr.geometric_factor(**p)
    return df


@pytest.mark.parametrize("array,params", [
    ("wenner", dict(a=np.geomspace(1, 60, 16))),
    ("pole_pole", dict(a=np.geomspace(1, 80, 16))),
    ("dipole_dipole", dict(a=np.repeat([2.0, 5.0, 10.0, 20.0], 4), n=np.tile([1, 2, 3, 4], 4))),
])
def test_inversion_all_array_types_recover_model(array, params):
    df = _synthetic(array, **params)
    res = invert_station(process_dataset(df, array), InversionConfig(n_layers=3, error_percent=2.0))
    assert res.rms_percent < 2.0
    np.testing.assert_allclose(res.resistivity[0], 100.0, rtol=0.2)
    assert res.metadata["array"] == array
    if array == "dipole_dipole":
        assert any("lateral profiling" in w for w in res.warnings)


def test_user_exclusion_removes_point_from_inversion(clean):
    import pandas as pd
    df = pd.read_csv(BENCH / "synthetic_schlumberger_3layer.csv")
    base = invert_station(process_dataset(df, "schlumberger"), InversionConfig(n_layers=3))
    excl = process_dataset(df, "schlumberger", excluded_rows={5})
    assert excl.table.qc_status[5] == "EXCLUDED" and excl.lineage["excluded_rows"] == [5]
    res = invert_station(excl, InversionConfig(n_layers=3))
    assert res.metadata["n_data"] == base.metadata["n_data"] - 1 and 5 not in res.metadata["rows_used"]
    assert res.run_id != base.run_id


def test_rejects_too_little_data():
    few = process_dataset(pd.read_csv(BENCH / "synthetic_schlumberger_3layer.csv").head(4), "schlumberger")
    with pytest.raises(InversionError, match="usable measurements"):
        invert_station(few, InversionConfig(n_layers=3))


def test_inversion_from_apparent_resistivity_with_unknown_mn(clean):
    """Real-data path: only AB/2 and rho_a supplied, MN/2 assumed point-electrode."""
    from app.inversion.forward import schlumberger_forward
    ab = np.array([1.5, 2, 3, 5, 7, 10, 15, 20, 30, 50, 70, 100, 150, 200.0])
    df = pd.DataFrame({"ab_half": ab, "apparent_resistivity": schlumberger_forward(ab, TRUE_RHO, TRUE_TH)})
    res = invert_station(process_dataset(df, "schlumberger", assume_point_mn=True),
                        InversionConfig(n_layers=3, error_percent=1.0))   # noise-free synthetic data
    np.testing.assert_allclose(res.resistivity, TRUE_RHO, rtol=0.05)
    np.testing.assert_allclose(res.thickness, TRUE_TH, rtol=0.10)
