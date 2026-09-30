import numpy as np

from .base import ElectrodeArray, general_geometric_factor


class PolePole(ElectrodeArray):
    """A=0 and M=a; B and N at infinity. K = 2 pi a (Loke 2004)."""
    name = "pole_pole"
    required_fields = ("a",)
    references = ("Loke (2004) Tutorial: 2-D and 3-D electrical imaging surveys",)

    def electrodes(self, a):
        a = np.asarray(a, float)
        inf = np.full_like(a, np.inf)
        return 0 * a, inf, a, inf

    def closed_form_k(self, a):
        return 2.0 * np.pi * np.asarray(a, float)

    def spacing(self, a):
        return np.asarray(a, float)

    def geometric_factor(self, a):
        return general_geometric_factor(*self.electrodes(a))

    def validate_row(self, row, index=None):
        return self._require_positive(row, index, "a")
