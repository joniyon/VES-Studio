import os

# Equivalence sampling is accurate but slow; most tests only need the inversion itself. Tests of the
# equivalence analysis set equivalence_samples explicitly.
os.environ.setdefault("VES_EQUIVALENCE_SAMPLES", "200")
