import numpy as np
import pytest

from app.units import UnitError, to_si


def test_conversions():
    assert to_si(150.0, "cm", "distance") == pytest.approx(1.5)
    assert to_si(0.2, "km", "distance") == pytest.approx(200.0)
    assert to_si(np.array([1.0, 2.0]), "mV", "voltage").tolist() == [0.001, 0.002]
    assert to_si(3.0, "kohm", "resistance") == 3000.0


def test_bad_unit_or_quantity():
    with pytest.raises(UnitError):
        to_si(1.0, "furlong", "distance")
    with pytest.raises(UnitError):
        to_si(1.0, "m", "mass")


def test_units_change_result_correctly():
    import pandas as pd
    from app.processing import process_dataset
    df = pd.DataFrame({"a": [1000.0], "resistance": [2.0]})
    r_m = process_dataset(df.assign(a=10.0), "wenner", {"distance": "m"})
    r_cm = process_dataset(df, "wenner", {"distance": "cm"})
    assert r_cm.table.apparent_resistivity[0] == pytest.approx(r_m.table.apparent_resistivity[0])
