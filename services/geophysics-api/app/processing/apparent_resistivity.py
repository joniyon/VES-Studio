"""Raw measurements -> array geometry -> geometric factor -> apparent resistivity.

Input is a table with canonical column names (column mapping happens upstream):
  array-specific distance columns (see ElectrodeArray.required_fields / integer_fields)
  and either `resistance`, or both `voltage` and `current`.
Problem rows are flagged, never silently deleted; rows with ERROR issues get
NaN results but remain in the output, linked to their source row.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app import ENGINE_VERSION
from app.arrays import get_array
from app.quality.issues import Issue, Severity
from app.units import to_si

DEFAULT_UNITS = {"distance": "m", "resistance": "ohm", "voltage": "V", "current": "A", "resistivity": "ohm-m"}
POINT_MN_FRACTION = 1e-3   # MN/2 as a fraction of AB/2 when MN is unknown (point-electrode limit)
JUMP_FACTOR = 3.0  # adjacent-spacing apparent-resistivity ratio that triggers a WARNING


@dataclass
class ProcessedDataset:
    table: pd.DataFrame
    issues: list[Issue]
    lineage: dict = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return any(i.severity is Severity.ERROR for i in self.issues)

    def issues_for_row(self, row: int) -> list[Issue]:
        return [i for i in self.issues if i.row == row]


def _fatal(msg, code, field_=None) -> ProcessedDataset:
    return ProcessedDataset(pd.DataFrame(), [Issue(Severity.ERROR, code, msg, None, field_)])


def process_dataset(df: pd.DataFrame, array_name: str, units: dict | None = None,
                    excluded_rows: set[int] | frozenset[int] | None = None,
                    assume_point_mn: bool = False) -> ProcessedDataset:
    units = {**DEFAULT_UNITS, **(units or {})}
    arr = get_array(array_name)
    geom_cols = list(arr.required_fields) + list(arr.integer_fields)

    if df is None or len(df) == 0:
        return _fatal("The dataset contains no rows.", "EMPTY_DATASET")

    point_mn = False
    if (assume_point_mn and arr.name == "schlumberger" and "mn_half" not in df.columns
            and "ab_half" in df.columns):
        # MN/2 not supplied: explicit, recorded point-electrode approximation (MN/2 = 0.1 % of AB/2)
        df = df.assign(mn_half=pd.to_numeric(df["ab_half"], errors="coerce") * POINT_MN_FRACTION)
        point_mn = True

    has_r = "resistance" in df.columns
    has_vi = "voltage" in df.columns and "current" in df.columns
    has_rho = "apparent_resistivity" in df.columns and not (has_r or has_vi)   # R, then V/I, take precedence
    missing = [c for c in geom_cols if c not in df.columns]
    if missing:
        return _fatal(f"Missing required column(s) for {arr.name}: {', '.join(missing)}.",
                      "MISSING_COLUMN", missing[0])
    if not (has_r or has_vi or has_rho):
        return _fatal("Provide 'resistance', or 'voltage' and 'current', or 'apparent_resistivity'.",
                      "MISSING_COLUMN", "resistance")

    issues: list[Issue] = []
    if point_mn:
        issues.append(Issue(Severity.WARNING, "MN_ASSUMED",
                            "MN/2 was not provided: the point-electrode approximation (MN/2 = 0.1 % of AB/2) is "
                            "used. Supply MN/2 to account for finite potential electrodes.", None, "mn_half"))
    raw = df.reset_index(drop=True)
    out = pd.DataFrame({"source_row": np.arange(len(raw))})

    # --- structural: numeric coercion --------------------------------------
    num = {}
    meas_cols = ["resistance"] if has_r else ["voltage", "current"] if has_vi else ["apparent_resistivity"]
    value_cols = geom_cols + meas_cols
    for c in value_cols:
        coerced = pd.to_numeric(raw[c], errors="coerce")
        bad = coerced.isna()
        for i in np.flatnonzero(bad):
            kind = "missing" if pd.isna(raw[c].iloc[i]) else "non-numeric"
            issues.append(Issue(Severity.ERROR, "VALUE_INVALID",
                                f"{c} is {kind}.", int(i), c))
        num[c] = coerced.to_numpy(dtype=float)

    # --- units -> SI --------------------------------------------------------
    si = {}
    for c in arr.required_fields:
        si[c] = to_si(num[c], units["distance"], "distance")
    for c in arr.integer_fields:
        si[c] = num[c]
    rho_given = None
    if has_rho:
        rho_given = to_si(num["apparent_resistivity"], units["resistivity"], "resistivity")
        resistance = np.full(len(raw), np.nan)        # derived below once K is known
    elif has_r:
        resistance = to_si(num["resistance"], units["resistance"], "resistance")
    else:
        with np.errstate(divide="ignore", invalid="ignore"):
            v = to_si(num["voltage"], units["voltage"], "voltage")
            i_ = to_si(num["current"], units["current"], "current")
            resistance = v / i_
        for i in np.flatnonzero(np.isfinite(num["current"]) & (num["current"] == 0)):
            issues.append(Issue(Severity.ERROR, "CURRENT_ZERO",
                                "current is zero; resistance is undefined.", int(i), "current"))
            resistance[i] = np.nan

    # --- duplicates -----------------------------------------------------------
    dup = raw[value_cols].duplicated(keep="first")
    for i in np.flatnonzero(dup.to_numpy()):
        issues.append(Issue(Severity.WARNING, "DUPLICATE_ROW",
                            "Duplicate measurement detected.", int(i)))

    # --- geometry validation ---------------------------------------------------
    for i in range(len(raw)):
        row = {c: si[c][i] for c in geom_cols}
        issues.extend(arr.validate_row(row, i))
    geom_bad = {i.row for i in issues if i.severity is Severity.ERROR and i.row is not None}

    # --- calculation (only rows without ERRORs) -----------------------------------
    ok = np.array([i not in geom_bad for i in range(len(raw))])
    k = np.full(len(raw), np.nan)
    if ok.any():
        params = {c: si[c][ok] for c in geom_cols}
        k[ok] = arr.geometric_factor(**params)
    if rho_given is not None:
        rho_a = rho_given.copy()
        with np.errstate(divide="ignore", invalid="ignore"):
            resistance = np.where(np.isfinite(k), rho_a / k, np.nan)
    else:
        rho_a = k * resistance
    rho_a[~ok] = np.nan
    if point_mn:
        k[:] = np.nan                                  # K/R are not defined without the real MN
        resistance = np.full(len(raw), np.nan)

    # --- measurement checks -------------------------------------------------------
    check = rho_a if (rho_given is not None or point_mn) else resistance
    for i in np.flatnonzero(ok):
        r = check[i]
        if not np.isfinite(r):
            continue
        if r == 0:
            issues.append(Issue(Severity.ERROR, "RESISTANCE_ZERO",
                                "Resistance is zero.", int(i), "resistance"))
            rho_a[i] = np.nan
        elif r < 0:
            issues.append(Issue(Severity.WARNING, "RESISTANCE_NEGATIVE",
                                "Negative resistance gives a negative apparent resistivity; "
                                "check polarity or self-potential.", int(i), "resistance"))

    spacing = np.full(len(raw), np.nan)
    if ok.any():
        spacing[ok] = arr.spacing(**{c: si[c][ok] for c in geom_cols})
    excluded = set(excluded_rows or ())
    not_excl = np.array([i not in excluded for i in range(len(raw))])
    valid = np.flatnonzero(np.isfinite(rho_a) & (rho_a > 0) & np.isfinite(spacing) & not_excl)
    order = valid[np.argsort(spacing[valid], kind="stable")]
    for prev, cur in zip(order[:-1], order[1:]):
        ratio = rho_a[cur] / rho_a[prev]
        if ratio > JUMP_FACTOR or ratio < 1 / JUMP_FACTOR:
            issues.append(Issue(Severity.WARNING, "ABRUPT_CHANGE",
                                "Large change in apparent resistivity between adjacent "
                                "spacings.", int(cur), "apparent_resistivity"))

    # --- assemble output -------------------------------------------------------------
    for c in geom_cols:
        out[c] = raw[c]
    for c in arr.required_fields:
        out[f"{c}_m"] = si[c]
    out["resistance_ohm"] = resistance
    out["geometric_factor"] = k
    out["apparent_resistivity"] = rho_a
    status = np.full(len(raw), "PASS", dtype=object)
    for i in sorted(excluded):
        if 0 <= i < len(raw):
            issues.append(Issue(Severity.INFO, "USER_EXCLUDED",
                                "Excluded from inversion by the user (value retained).", i))
    for iss in issues:
        if iss.row is None:
            continue
        if iss.severity is Severity.ERROR:
            status[iss.row] = "ERROR"
        elif iss.severity is Severity.WARNING and status[iss.row] != "ERROR":
            status[iss.row] = "WARNING"
    for i in excluded:
        if 0 <= i < len(raw) and status[i] != "ERROR":
            status[i] = "EXCLUDED"
    out["qc_status"] = status

    n_pass = int((status == "PASS").sum())
    n_excl = int((status == "EXCLUDED").sum())
    issues.append(Issue(Severity.INFO, "SUMMARY",
                        f"{n_pass} of {len(raw)} measurements passed validation"
                        + (f" ({n_excl} excluded by user)." if n_excl else ".")))

    lineage = {
        "engine_version": ENGINE_VERSION,
        "array": arr.name,
        "units": units,
        "columns_used": value_cols,
        "measurement": "apparent_resistivity" if has_rho else "resistance" if has_r else "voltage_current",
        "mn_half_assumed": point_mn,
        "excluded_rows": sorted(i for i in excluded if 0 <= i < len(raw)),
        "references": list(arr.references),
        "formula": "rho_a = K * (dV / I),  K from electrode geometry (see array.references)",
    }
    return ProcessedDataset(out, issues, lineage)
