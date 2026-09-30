# Lithology interpretation

**Principle:** resistivity does not identify lithology. The platform keeps the *measured/calculated*
model (layer ρ, thickness, depth) strictly separate from the *interpretation* (lithology, confidence, basis, notes),
which belongs to the user.

## Suggestions
`app/interpretation/suggest.py` ranks **possible** lithologies for a layer by (a) whether ρ lies inside an
indicative range and (b) whether the layer depth is plausible for that material (e.g. topsoil at 40 m is not).
It returns several candidates with a plain-language basis. It never returns one answer and never a confidence;
confidence (low / medium / high) is set by the user.

## Ranges
Indicative, broad and overlapping, compiled from commonly quoted tables (Telford et al. 1990;
Keller & Frischknecht 1966; Reynolds 2011) plus typical basement-complex hydrogeology practice.
**All `verified=False`** — each bound must be checked against the primary tables before V1 sign-off
(a test enforces that the flag is only flipped deliberately).

## Display conventions
Colours and fill patterns follow common lithologic-column practice (stipple = sand, circles = gravel,
dashes = clay/shale, crosses/bricks = carbonate and crystalline rock). Patterns are matplotlib hatches, used
identically in the UI, exported figures and the PDF. This is **not** a formal implementation of FGDC-STD-013-2006;
mapping to its numbered patterns is future work. Every (colour, hatch) pair is unique so columns stay readable in
black-and-white.
