import numpy as np

from app.quality.issues import Issue, Severity
from .base import ElectrodeArray, general_geometric_factor


class Gradient(ElectrodeArray):
    """Gradient (rectangle) array: fixed current electrodes A=-AB/2, B=+AB/2 and a
    movable potential dipole of length MN centred at offset x from the array centre.
    K from the general four-electrode formula (Telford et al. 1990; Reynolds 2011).
    Measurements are conventionally taken within the middle third of AB."""
    name = "gradient"
    required_fields = ("ab", "mn", "x")
    references = ("Telford, Geldart & Sheriff (1990) ch. 8",
                  "Reynolds (2011) Intro. to Applied and Environmental Geophysics, 2nd ed.")

    def electrodes(self, ab, mn, x):
        ab, mn, x = (np.asarray(v, float) for v in (ab, mn, x))
        return -ab / 2, ab / 2, x - mn / 2, x + mn / 2

    def closed_form_k(self, ab, mn, x):
        return general_geometric_factor(*self.electrodes(ab, mn, x))

    def spacing(self, ab, mn, x):
        return np.asarray(x, float)

    def validate_row(self, row, index=None):
        issues = self._require_positive(row, index, "ab", "mn")
        x = row.get("x")
        if x is None or not np.isfinite(x):
            issues.append(Issue(Severity.ERROR, "GEOM_MISSING_X",
                                "x (MN centre offset) is required.", index, "x"))
        if issues:
            return issues
        ab, mn = row["ab"], row["mn"]
        if mn >= ab:
            issues.append(Issue(Severity.ERROR, "GEOM_MN_GE_AB",
                                "MN must be smaller than AB.", index, "mn"))
        elif abs(x) + mn / 2 >= ab / 2:
            issues.append(Issue(Severity.ERROR, "GEOM_MN_OUTSIDE_AB",
                                "MN dipole lies outside (or on) a current electrode.",
                                index, "x"))
        elif abs(x) > ab / 6:
            issues.append(Issue(Severity.WARNING, "GEOM_OUTSIDE_MIDDLE_THIRD",
                                "MN centre is outside the middle third of AB.", index, "x"))
        return issues
