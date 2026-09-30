import numpy as np

from app.quality.issues import Issue, Severity
from .base import ElectrodeArray


class Schlumberger(ElectrodeArray):
    """Symmetric collinear array, A M N B. L = AB/2, l = MN/2.
    K = pi (L^2 - l^2) / (2 l)   (Telford et al. 1990; Koefoed 1979)
    """
    name = "schlumberger"
    required_fields = ("ab_half", "mn_half")
    references = ("Telford, Geldart & Sheriff (1990) ch. 8",
                  "Koefoed (1979) Geosounding Principles 1")

    def electrodes(self, ab_half, mn_half):
        L, l = np.asarray(ab_half, float), np.asarray(mn_half, float)
        return -L, L, -l, l

    def closed_form_k(self, ab_half, mn_half):
        L, l = np.asarray(ab_half, float), np.asarray(mn_half, float)
        return np.pi * (L**2 - l**2) / (2.0 * l)

    def spacing(self, ab_half, mn_half):
        return np.asarray(ab_half, float)

    def validate_row(self, row, index=None):
        issues = self._require_positive(row, index, "ab_half", "mn_half")
        if issues:
            return issues
        L, l = row["ab_half"], row["mn_half"]
        if l >= L:
            issues.append(Issue(Severity.ERROR, "GEOM_MN_GE_AB",
                                "MN/2 must be smaller than AB/2.", index, "mn_half"))
        elif l > L / 5:
            # Practical rule of thumb: MN <= AB/5 keeps the point-electrode
            # approximation acceptable (Koefoed 1979; Reynolds 2011).
            issues.append(Issue(Severity.WARNING, "GEOM_MN_LARGE",
                                "MN/2 exceeds AB/2 / 5; the Schlumberger approximation "
                                "may be poor.", index, "mn_half"))
        return issues
