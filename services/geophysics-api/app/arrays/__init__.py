from .base import ElectrodeArray, general_geometric_factor
from .dipole_dipole import DipoleDipole
from .gradient import Gradient
from .pole_dipole import PoleDipole
from .pole_pole import PolePole
from .schlumberger import Schlumberger
from .wenner import Wenner

REGISTRY: dict[str, ElectrodeArray] = {
    a.name: a for a in (Schlumberger(), Wenner(), DipoleDipole(), PoleDipole(), PolePole(), Gradient())
}


def get_array(name: str) -> ElectrodeArray:
    try:
        return REGISTRY[name]
    except KeyError:
        raise ValueError(f"Unknown array '{name}'. Supported: {', '.join(REGISTRY)}.") from None
