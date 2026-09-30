# V1 acceptance status

Checked against section 36 of the scope. "Evidence" points to the test or UI feature.

| Criterion | Status | Evidence / caveat |
|---|---|---|
| CSV/XLSX upload works | Done | CSV in browser; XLSX via `/parse-xlsx` (`tests/test_api.py`), sheet picker, SHA-256 recorded |
| Column mapping works | Done | Auto-detect + manual override with ✓/✗ per field |
| All six arrays work | Done | Processing for all six; inversion for all six (see note) |
| Array validation works | Done | `tests/test_processing.py` |
| Geometric factors validated | Done, with gap | Closed form vs general formula vs half-space vs pyGIMLi (1e-9). **Gap: no published worked examples with page citations yet** |
| Apparent-resistivity tests | Done | `tests/test_arrays.py`, `tests/test_processing.py` |
| Units handled | Done | `tests/test_units.py`; explicit unit selectors in UI |
| Invalid datasets → understandable errors | Done | Flagged per row, never silently dropped |
| QC works | Done | INFO/WARNING/ERROR, user exclusion of points |
| Curves render correctly | Done | Log-log, hover, click-to-inspect, zoom/pan |
| 1D inversion works | Done | pyGIMLi backend; all arrays. Schlumberger cross-checked against pyGIMLi; other arrays verified by layered-forward agreement with pyGIMLi (1e-5) and synthetic model recovery |
| Layer parameters returned | Done | ρ, thickness, top/bottom depth |
| Model curves generated | Done | Observed vs model on one plot |
| RMS / error displayed | Done | RMS %, χ², iterations, converged flag |
| Inversion reproducible | Done | Stable run ID; session restore recomputes identical run IDs |
| Subsurface model visualised | Done | Resistivity-depth profile + geological column with lithology colours/hatches |
| Report generation works | Done | PDF (`tests/test_reports.py`), plus CSV/PNG/SVG/JSON/project-file exports |
| **Real VES dataset upload → report** | **Not verified** | Only synthetic data has been run end to end. Needs a real field dataset |

## Also delivered
Project and station metadata (with coordinate validation), processing history, autosave, project-file save/open
(keeps the original upload), lithology interpretation with ranked suggestions and user-set confidence,
geological context, draft conclusion.

## Open items before calling V1 final
1. Run a real field dataset through upload → report and review the output with a geophysicist.
2. Verify references and every lithology resistivity range against primary sources (`verified=False`).
3. Add published worked examples (with citations) to the validation suite.
4. Decide on a persistence backend (database/auth). V1 currently stores work in the browser plus portable project files.
5. Map lithology patterns to FGDC-STD-013-2006 if formal compliance is wanted.
6. Inversion for profiling arrays (dipole-dipole, pole-dipole, gradient) is technically supported but of limited
   geophysical meaning as a single-location 1D model; the UI/report warns about this.
