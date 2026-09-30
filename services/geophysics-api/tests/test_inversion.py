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


def test_rejects_non_schlumberger_and_too_little_data(clean):
    wen = process_dataset(pd.DataFrame({"a": [1, 2, 4, 8], "resistance": [5, 4, 3, 2.5]}), "wenner")
    with pytest.raises(InversionError, match="Schlumberger"):
        invert_station(wen)
    few = process_dataset(pd.read_csv(BENCH / "synthetic_schlumberger_3layer.csv").head(4), "schlumberger")
    with pytest.raises(InversionError, match="usable measurements"):
        invert_station(few, InversionConfig(n_layers=3))
