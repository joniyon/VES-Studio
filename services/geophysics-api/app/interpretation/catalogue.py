"""Lithology catalogue: display conventions + INDICATIVE resistivity ranges.

Display: conventional lithologic-column colours and fill patterns following common geological
practice (e.g. stipple = sand, circles = gravel, dashes = clay/shale, bricks/crosses = carbonate,
random/cross = crystalline rock). Patterns are drawn with matplotlib hatches. This is NOT a formal
implementation of the FGDC Digital Cartographic Standard for Geologic Map Symbolization
(FGDC-STD-013-2006); mapping to its numbered patterns is listed as future work.

Resistivity ranges: broad, overlapping, indicative values compiled from the commonly quoted tables
(Telford et al. 1990; Keller & Frischknecht 1966; Reynolds 2011) plus typical basement-complex
hydrogeology practice. They are NOT diagnostic - saturation, pore-water salinity, clay content
and temperature move a material across these ranges. `verified=False` until each bound is checked
against the primary tables (see scientific/references/references.md).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Lithology:
    id: str
    name: str
    group: str
    color: str            # face colour (hex)
    hatch: str            # matplotlib hatch string
    rho_min: float        # ohm-m, indicative
    rho_max: float
    depth_min: float = 0.0     # soft plausibility band for layer top depth (m)
    depth_max: float | None = None
    verified: bool = False


CATALOGUE: tuple[Lithology, ...] = (
    Lithology("topsoil", "Topsoil / organic soil", "Surficial", "#8B6B4A", "..", 30, 600, 0, 3),
    Lithology("laterite", "Laterite / lateritic soil", "Surficial", "#C0694A", "oo", 100, 1500, 0, 10),
    Lithology("clay", "Clay", "Unconsolidated", "#9DB88D", "-", 1, 100),
    Lithology("sandy_clay", "Sandy clay / clayey sand", "Unconsolidated", "#C9C58A", "-.", 20, 200),
    Lithology("silt", "Silt", "Unconsolidated", "#BFC9A0", "..--", 10, 150),
    Lithology("sand", "Sand", "Unconsolidated", "#F3E19A", "..", 60, 1000),
    Lithology("gravel", "Gravel", "Unconsolidated", "#F1B77A", "OO", 150, 2500),
    Lithology("sandstone", "Sandstone", "Sedimentary", "#E5C27A", "....", 100, 5000),
    Lithology("shale", "Shale / mudstone", "Sedimentary", "#A9ADB3", "--", 20, 1000),
    Lithology("limestone", "Limestone", "Sedimentary", "#A8CBE8", "++", 100, 10000),
    Lithology("weathered_basement", "Weathered basement (saprolite)", "Crystalline", "#EBB9B0", "//", 30, 250, 0.5, 80),
    Lithology("fractured_basement", "Fractured basement", "Crystalline", "#D98C85", "x", 100, 800, 3, 150),
    Lithology("fresh_basement", "Fresh basement (granite / gneiss)", "Crystalline", "#C25E5E", "xx", 800, 100000, 3),
    Lithology("volcanic", "Basalt / volcanic rock", "Igneous", "#7E8B84", "\\\\", 200, 100000, 0),
    Lithology("unclassified", "Unclassified / undetermined", "Other", "#FFFFFF", "", 0, 1e9),
)
BY_ID = {l.id: l for l in CATALOGUE}


def get_lithology(lid: str) -> Lithology:
    try:
        return BY_ID[lid]
    except KeyError:
        raise ValueError(f"Unknown lithology '{lid}'.") from None
