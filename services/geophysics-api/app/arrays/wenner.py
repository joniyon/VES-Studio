import numpy as np

from .base import ElectrodeArray


class Wenner(ElectrodeArray):
    """Equally spaced A M N B with spacing a. K = 2 pi a (Wenner 1915)."""
    name = "wenner"
    required_fields = ("a",)
    references = ("Wenner (1915) Bull. Bur. Standards 12(4)",
                  "Telford, Geldart & Sheriff (1990) ch. 8")

    def electrodes(self, a):
        a = np.asarray(a, float)
        return -1.5 * a, 1.5 * a, -0.5 * a, 0.5 * a

    def closed_form_k(self, a):
        return 2.0 * np.pi * np.asarray(a, float)

    def spacing(self, a):
        return np.asarray(a, float)

    def validate_row(self, row, index=None):
        return self._require_positive(row, index, "a")
