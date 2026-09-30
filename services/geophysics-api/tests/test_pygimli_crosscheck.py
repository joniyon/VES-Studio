"""Independent cross-check of geometric factors against pyGIMLi (skipped if unavailable)."""
import numpy as np
import pytest

from tests.test_arrays import CASES
from app.arrays import get_array

pg = pytest.importorskip("pygimli")
from pygimli.physics import ert  # noqa: E402


def pygimli_k(A, B, M, N):
    d = pg.DataContainerERT()
    ids = {}
    for x in (A, B, M, N):
        if not np.isinf(x) and x not in ids:
            ids[x] = d.createSensor([x, 0, 0])
    g = lambda x: -1 if np.isinf(x) else ids[x]
    d.createFourPointData(0, g(A), g(B), g(M), g(N))
    return abs(ert.geometricFactors(d, dim=3)[0])


@pytest.mark.parametrize("name", list(CASES))
def test_geometric_factor_matches_pygimli(name):
    arr = get_array(name)
    p = {k: np.array(v, float) for k, v in CASES[name].items()}
    ours = arr.geometric_factor(**p)
    for i in range(len(ours)):
        row = {k: v[i] for k, v in p.items()}
        pos = [float(x) for x in np.broadcast_arrays(*arr.electrodes(**row))]
        assert ours[i] == pytest.approx(pygimli_k(*pos), rel=1e-9)
