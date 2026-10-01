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


def _segmented_sounding(offsets=(1.0, 0.8, 1.25, 0.9, 1.1, 0.7), spike_at=None):
    from app.processing.working_curve import segment_ids
    ab = np.array([1.5, 2, 3, 5, 6, 6, 8, 12, 15, 15, 25, 32, 40, 40, 50, 65, 80, 100, 100, 120, 150, 200, 200, 250.0])
    from app.inversion.forward import schlumberger_forward
    seg = segment_ids(ab)
    rho_a = schlumberger_forward(ab, TRUE_RHO, TRUE_TH) * np.array(offsets)[seg]
    if spike_at is not None:
        rho_a[spike_at] *= 5.0
    return pd.DataFrame({"ab_half": ab, "apparent_resistivity": rho_a})


def test_working_curve_inversion_beats_raw_on_offset_segments_and_reports_both_misfits():
    from app.processing import WorkingCurveConfig
    p = process_dataset(_segmented_sounding(), "schlumberger", assume_point_mn=True)
    raw = invert_station(p, InversionConfig(n_layers=3, error_percent=2.0))
    shifted = invert_station(p, InversionConfig(n_layers=3, error_percent=2.0,
                                                working=WorkingCurveConfig(overlap="shift")))
    assert shifted.rms_raw_percent is not None and shifted.rms_percent < 1.0
    assert shifted.rms_percent < raw.rms_percent                      # working curve is self-consistent
    np.testing.assert_allclose(shifted.resistivity, TRUE_RHO, rtol=0.1)
    np.testing.assert_allclose(shifted.thickness, TRUE_TH, rtol=0.15)
    assert shifted.metadata["n_raw"] == 24 and shifted.metadata["n_data"] == 19
    assert shifted.working["n_segments"] == 6 and len(shifted.working["shifts"]) == 6
    assert any("working curve" in w for w in shifted.warnings)
    assert raw.run_id != shifted.run_id and raw.working == {}


def test_average_plus_median_is_more_robust_to_outliers_than_raw_fit():
    """Measured property (see docs/science/working-curve.md): with isolated outliers, merging overlaps and
    median smoothing recovers the model better than fitting the raw readings (median over seeds)."""
    from app.processing import WorkingCurveConfig
    from app.inversion.forward import schlumberger_forward
    df0 = _segmented_sounding(offsets=(1.0,) * 6)
    ab = df0.ab_half.to_numpy()
    true = schlumberger_forward(ab, TRUE_RHO, TRUE_TH)
    raw_err, sm_err = [], []
    for seed in range(8):
        rng = np.random.default_rng(seed)
        y = true * np.exp(rng.normal(0, 0.05, len(ab)))
        idx = rng.choice(len(ab), 3, replace=False)
        y[idx] *= np.exp(rng.choice([-1, 1], 3) * np.log(4.0))
        p = process_dataset(pd.DataFrame({"ab_half": ab, "apparent_resistivity": y}), "schlumberger", assume_point_mn=True)
        err = lambda r: np.max(np.abs(np.log(r.resistivity / TRUE_RHO)))
        raw_err.append(err(invert_station(p, InversionConfig(n_layers=3, error_percent=10.0))))
        sm_err.append(err(invert_station(p, InversionConfig(
            n_layers=3, error_percent=10.0, working=WorkingCurveConfig(overlap="average", smooth="median")))))
    assert np.median(sm_err) < np.median(raw_err)


def test_working_curve_runs_are_reproducible_and_config_sensitive():
    from app.processing import WorkingCurveConfig
    p = process_dataset(_segmented_sounding(), "schlumberger", assume_point_mn=True)
    mk = lambda **w: invert_station(p, InversionConfig(n_layers=3, working=WorkingCurveConfig(**w)))
    a, b = mk(overlap="shift"), mk(overlap="shift")
    assert a.run_id == b.run_id
    np.testing.assert_array_equal(a.resistivity, b.resistivity)
    assert mk(overlap="shift", smooth="median").run_id != a.run_id


def test_working_curve_rejected_for_profiling_arrays_and_too_few_points():
    from app.processing import WorkingCurveConfig
    dd = process_dataset(pd.DataFrame({"a": np.repeat([2.0, 5.0, 10.0, 20.0], 4), "n": np.tile([1, 2, 3, 4], 4),
                                        "apparent_resistivity": np.linspace(10, 40, 16)}), "dipole_dipole")
    with pytest.raises(InversionError, match="soundings only"):
        invert_station(dd, InversionConfig(n_layers=3, working=WorkingCurveConfig(overlap="average")))
    few = process_dataset(_segmented_sounding().head(8), "schlumberger", assume_point_mn=True)
    with pytest.raises(InversionError):
        invert_station(few, InversionConfig(n_layers=5, working=WorkingCurveConfig(smooth="median")))


def test_merged_overlaps_are_evaluated_at_each_raw_mn_not_an_averaged_mn():
    """Averaging repeated spacings must not invent an averaged MN/2: the backend sees one datum per raw row."""
    from app.inversion.pygimli_backend import PygimliBackend
    from app.processing import WorkingCurveConfig
    ab = np.array([1.0, 2, 4, 6, 6, 10, 15, 15, 25, 40, 40, 65])
    mn = np.array([0.25, 0.25, 0.25, 0.25, 0.5, 0.5, 0.5, 1.0, 1.0, 1.0, 2.5, 2.5])
    from app.inversion.forward import schlumberger_forward
    df = pd.DataFrame({"ab_half": ab, "mn_half": mn, "apparent_resistivity": schlumberger_forward(ab, TRUE_RHO, TRUE_TH)})
    seen = {}

    class Spy(PygimliBackend):
        def invert(self, spacing, distances, observed, cfg, error_scale=None):
            seen.update(am=distances["am"], an=distances["an"], err=error_scale, n=len(observed))
            return super().invert(spacing, distances, observed, cfg, error_scale)

    r = invert_station(process_dataset(df, "schlumberger"),
                       InversionConfig(n_layers=3, working=WorkingCurveConfig(overlap="average")), backend=Spy())
    assert seen["n"] == len(ab) and len(r.spacing) == 9            # 12 raw configs behind 9 working points
    half_mn = (seen["an"] - seen["am"]) / 2                           # recovers each datum's own MN/2 (a_pos = -AB/2)
    assert sorted(set(np.round(half_mn, 3))) == [0.25, 0.5, 1.0, 2.5]   # no 0.375 / 0.75 / 1.75 averages
    assert np.isclose(seen["err"], [1, 1, 1, 2**.5, 2**.5, 1, 2**.5, 2**.5, 1, 2**.5, 2**.5, 1]).all()
    assert len(r.model_response) == len(r.observed) == 9
