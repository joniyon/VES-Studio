import numpy as np

from .base import ElectrodeArray, general_geometric_factor
from .dipole_dipole import _validate_a_n


class PoleDipole(ElectrodeArray):
    """Forward pole-dipole: A=0, M=n a, N=(n+1) a; B (and nothing else) at infinity.
    K = 2 pi n (n+1) a  (Loke 2004)."""
    name = "pole_dipole"
    required_fields = ("a",)
    integer_fields = ("n",)
    references = ("Loke (2004) Tutorial: 2-D and 3-D electrical imaging surveys",)

    def electrodes(self, a, n):
        a, n = np.asarray(a, float), np.asarray(n, float)
        return 0 * a, np.full_like(a * n, np.inf), n * a, (n + 1) * a

    def closed_form_k(self, a, n):
        a, n = np.asarray(a, float), np.asarray(n, float)
        return 2.0 * np.pi * n * (n + 1) * a

    def spacing(self, a, n):
        return np.asarray(a, float) * (np.asarray(n, float) + 0.5)

    def geometric_factor(self, a, n):
        return general_geometric_factor(*self.electrodes(a, n))

    def validate_row(self, row, index=None):
        return _validate_a_n(self, row, index)
