"""Explicit unit handling. All internal calculations use SI base units:
metres, ohms, volts, amperes, ohm-metres. Conversions are never implicit."""

DISTANCE = {"m": 1.0, "cm": 0.01, "km": 1000.0}
RESISTANCE = {"ohm": 1.0, "mohm": 1e-3, "kohm": 1e3}
VOLTAGE = {"V": 1.0, "mV": 1e-3}
CURRENT = {"A": 1.0, "mA": 1e-3}
RESISTIVITY = {"ohm-m": 1.0, "kohm-m": 1e3}

_TABLES = {
    "distance": DISTANCE,
    "resistance": RESISTANCE,
    "voltage": VOLTAGE,
    "current": CURRENT,
    "resistivity": RESISTIVITY,
}


class UnitError(ValueError):
    pass


def to_si(values, unit: str, quantity: str):
    """Convert `values` (scalar or array-like) expressed in `unit` to SI."""
    table = _TABLES.get(quantity)
    if table is None:
        raise UnitError(f"Unknown quantity '{quantity}'. Expected one of {sorted(_TABLES)}.")
    if unit not in table:
        raise UnitError(
            f"Unsupported {quantity} unit '{unit}'. Supported: {', '.join(table)}."
        )
    return values * table[unit]
