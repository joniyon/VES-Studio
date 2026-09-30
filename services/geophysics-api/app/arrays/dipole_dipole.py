import numpy as np

from .base import ElectrodeArray


class DipoleDipole(ElectrodeArray):
    """A B ... M N with dipole length a and separation factor n:
    A=0, B=a, M=(n+1)a, N=(n+2)a.  K = pi n (n+1) (n+2) a  (Loke 2004)."""
    name = "dipole_dipole"
    required_fields = ("a",)
    integer_fields = ("n",)
    references = ("Loke (2004) Tutorial: 2-D and 3-D electrical imaging surveys",
                  "Telford, Geldart & Sheriff (1990) ch. 8")

    def electrodes(self, a, n):
        a, n = np.asarray(a, float), np.asarray(n, float)
        return 0 * a, a, (n + 1) * a, (n + 2) * a

    def closed_form_k(self, a, n):
        a, n = np.asarray(a, float), np.asarray(n, float)
        return np.pi * n * (n + 1) * (n + 2) * a

    def spacing(self, a, n):
        return np.asarray(a, float) * (np.asarray(n, float) + 1)  # dipole midpoint separation

    def geometric_factor(self, a, n):
        # Use the general formula as the operational path; the closed form is
        # checked against it in the test suite.
        from .base import general_geometric_factor
        return general_geometric_factor(*self.electrodes(a, n))

    def validate_row(self, row, index=None):
        return _validate_a_n(self, row, index)


def _validate_a_n(arr, row, index):
    from app.quality.issues import Issue, Severity
    issues = arr._require_positive(row, index, "a")
    n = row.get("n")
    if n is None or not np.isfinite(n) or n < 1 or n != int(n):
        issues.append(Issue(Severity.ERROR, "GEOM_BAD_N",
                            "n must be a positive integer.", index, "n"))
    elif n > 8:
        issues.append(Issue(Severity.WARNING, "GEOM_N_LARGE",
                           "n > 8: signal strength is typically very low.", index, "n"))
    return issues
