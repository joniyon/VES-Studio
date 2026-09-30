# Working curve (data preparation before inversion)

Raw readings are never modified. Optionally the inversion fits a *working curve* derived from them:

| Step | What it does | Risk |
|---|---|---|
| **Shift** | Multiplies each measurement segment (new segment wherever a spacing repeats = MN change) so repeated spacings agree with the neighbouring segment; anchor segment stays at 1.0 | One noisy overlap pair sets a whole segment's factor; can make results **worse** |
| **Average** | Repeated spacings → one point (geometric mean) | Hides disagreement between the two readings |
| **Median / Hanning smoothing** | Running median (or weighted mean) of log ρa over 3 or 5 neighbouring spacings; windows shrink at the ends | Slightly biases clean curves, can flatten real thin layers |

Only for single-spacing sounding arrays (Schlumberger, Wenner, pole-pole). The choice is part of the run ID,
the processing history and the PDF; the result reports the misfit against **both** the working curve and the raw data.

## Measured behaviour (Monte Carlo, 12 seeds, 3-layer model, metric = worst layer's |ln(recovered/true)|, median)

| Scenario | Raw | Shift | Shift + median | Average + median |
|---|---|---|---|---|
| Noise-free | 0.29 | 0.36 | 0.38 | 0.38 |
| 10 % noise | 0.32 | 0.64 | 0.73 | 0.41 |
| True 20 % segment offsets | 0.50 | 0.45 | 0.48 | 0.55 |
| 3 outliers (×4) | 0.86 | 1.43 | 1.12 | **0.44** |
| 15 % noise + offsets + outliers | 1.17 | 1.62 | 1.08 | **0.53** |

**Guidance:** for erratic field data, *average overlaps + median smoothing* is the most robust. Use *shift* only when the
offsets look systematic (e.g. every second reading lower by a similar factor) — not to tidy up scatter. Smoothing trades a
little accuracy on clean data for robustness to bad readings.

## Relation to WinResist
WinResist reports "RMS on smoothed data" and fits a smoothed curve. Its exact smoothing algorithm is not documented here, so
results will not match number-for-number. Independent checks that do hold: for WinResist's published VES 1 layer model, this
engine's forward model and pyGIMLi agree to ~6e-8; for VES 2 the top layer (8.8 Ωm, 1.4 m) and the conductive layer
(~0.6–0.7 Ωm, ~2–12 m) agree closely; deeper layers differ (poorly resolved with noisy data).
