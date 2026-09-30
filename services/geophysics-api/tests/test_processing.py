import numpy as np
import pandas as pd
import pytest

from app.processing import process_dataset
from app.quality import Severity


def codes(res, sev=None):
    return [i.code for i in res.issues if sev is None or i.severity is sev]


def test_schlumberger_end_to_end():
    K = np.pi * (10**2 - 1**2) / 2
    df = pd.DataFrame({"ab_half": [10.0], "mn_half": [1.0], "resistance": [2.0]})
    res = process_dataset(df, "schlumberger")
    assert res.table.geometric_factor[0] == pytest.approx(K)
    assert res.table.apparent_resistivity[0] == pytest.approx(2.0 * K)
    assert res.table.qc_status[0] == "PASS"
    assert "1 of 1 measurements passed" in str(res.issues[-1])
    assert res.lineage["array"] == "schlumberger" and res.lineage["engine_version"]


def test_voltage_current_path():
    df = pd.DataFrame({"a": [10.0], "voltage": [50.0], "current": [100.0]})
    df_mA = process_dataset(df, "wenner", {"voltage": "mV", "current": "mA"})
    assert df_mA.table.resistance_ohm[0] == pytest.approx(0.5)
    assert df_mA.table.apparent_resistivity[0] == pytest.approx(2 * np.pi * 10 * 0.5)


def test_empty_dataset():
    res = process_dataset(pd.DataFrame(), "wenner")
    assert res.has_errors and codes(res) == ["EMPTY_DATASET"]


def test_missing_columns():
    res = process_dataset(pd.DataFrame({"a": [1.0]}), "wenner")
    assert codes(res) == ["MISSING_COLUMN"]
    res = process_dataset(pd.DataFrame({"resistance": [1.0]}), "wenner")
    assert "MISSING_COLUMN" in codes(res)


def test_invalid_values_flagged_not_dropped():
    df = pd.DataFrame({"ab_half": [10, 20, "x", 40], "mn_half": [1, None, 1, 1],
                       "resistance": [2, 2, 2, 0.125]})
    res = process_dataset(df, "schlumberger")
    assert len(res.table) == 4                               # nothing deleted
    assert res.table.qc_status.tolist() == ["PASS", "ERROR", "ERROR", "PASS"]
    assert np.isnan(res.table.apparent_resistivity[1:3]).all()
    assert {i.row for i in res.issues if i.code == "VALUE_INVALID"} == {1, 2}


def test_geometry_errors():
    df = pd.DataFrame({"ab_half": [5.0, 10.0, 10.0], "mn_half": [6.0, 3.0, 1.0],
                       "resistance": [1.0, 1.0, 0.3]})
    res = process_dataset(df, "schlumberger")
    assert "GEOM_MN_GE_AB" in codes(res, Severity.ERROR)
    assert "GEOM_MN_LARGE" in codes(res, Severity.WARNING)
    assert res.table.qc_status.tolist() == ["ERROR", "WARNING", "PASS"]


def test_duplicate_and_abrupt_change():
    df = pd.DataFrame({"a": [1, 2, 2, 4, 8], "resistance": [10, 10, 10, 10, 200]})
    res = process_dataset(df, "wenner")
    assert (codes(res).count("DUPLICATE_ROW"), 2) == (1, 2) and \
        next(i for i in res.issues if i.code == "DUPLICATE_ROW").row == 2
    jump = [i for i in res.issues if i.code == "ABRUPT_CHANGE"]
    assert len(jump) == 1 and jump[0].row == 4


def test_zero_current_and_zero_resistance():
    df = pd.DataFrame({"a": [1.0, 2.0], "voltage": [1.0, 1.0], "current": [0.0, 1.0]})
    assert "CURRENT_ZERO" in codes(process_dataset(df, "wenner"))
    res = process_dataset(pd.DataFrame({"a": [1.0], "resistance": [0.0]}), "wenner")
    assert "RESISTANCE_ZERO" in codes(res) and np.isnan(res.table.apparent_resistivity[0])


def test_negative_resistance_warns():
    res = process_dataset(pd.DataFrame({"a": [1.0], "resistance": [-1.0]}), "wenner")
    assert "RESISTANCE_NEGATIVE" in codes(res, Severity.WARNING)


def test_dipole_dipole_bad_n():
    df = pd.DataFrame({"a": [10.0, 10.0], "n": [1.5, 2], "resistance": [1.0, 1.0]})
    res = process_dataset(df, "dipole_dipole")
    assert res.table.qc_status.tolist() == ["ERROR", "PASS"]


def test_gradient_geometry():
    df = pd.DataFrame({"ab": [100.0, 100.0, 100.0], "mn": [5.0, 5.0, 5.0],
                       "x": [0.0, 30.0, 60.0], "resistance": [1.0, 1.0, 1.0]})
    res = process_dataset(df, "gradient")
    assert res.table.qc_status.tolist() == ["PASS", "WARNING", "ERROR"]


@pytest.mark.parametrize("array,cols", [
    ("wenner", {"a": [1, 2, 4]}), ("pole_pole", {"a": [1, 2, 4]}),
    ("pole_dipole", {"a": [5, 5], "n": [1, 2]}), ("dipole_dipole", {"a": [5, 5], "n": [1, 2]}),
])
def test_all_arrays_process(array, cols):
    df = pd.DataFrame({**cols, "resistance": [1.0] * len(next(iter(cols.values())))})
    res = process_dataset(df, array)
    assert not res.has_errors and res.table.geometric_factor.notna().all()


def test_reproducible():
    df = pd.DataFrame({"a": [1, 2, 4, 8], "resistance": [5, 4, 3, 2]})
    a, b = process_dataset(df, "wenner"), process_dataset(df, "wenner")
    pd.testing.assert_frame_equal(a.table, b.table)
