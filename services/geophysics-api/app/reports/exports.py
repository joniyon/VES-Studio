"""CSV exports: processed data, layer model."""
import csv
import io

from app.interpretation import get_lithology


def processed_csv(processed) -> str:
    t = processed.table.copy()
    by_row: dict[int, list[str]] = {}
    for i in processed.issues:
        if i.row is not None:
            by_row.setdefault(i.row, []).append(f"{i.severity.value}: {i.message}")
    t["qc_messages"] = [" | ".join(by_row.get(int(r), [])) for r in t.source_row]
    meta = (f"# VES Studio processed data | engine {processed.lineage.get('engine_version')} | "
            f"array {processed.lineage.get('array')} | units {processed.lineage.get('units')}\n")
    return meta + t.to_csv(index=False)


def layers_csv(result, interpretation: list[dict] | None = None) -> str:
    interp = list(interpretation or [])
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["layer", "resistivity_ohm_m", "thickness_m", "depth_top_m", "depth_bottom_m",
                "lithology", "confidence", "basis", "notes", "run_id"])
    n = len(result.resistivity)
    for i in range(n):
        it = interp[i] if i < len(interp) else {}
        lit = get_lithology(it.get("lithology") or "unclassified")
        bottom = "" if result.depth_bottom[i] in (None, float("inf")) else f"{result.depth_bottom[i]:.6g}"
        w.writerow([i + 1, f"{result.resistivity[i]:.6g}",
                    f"{result.thickness[i]:.6g}" if i < n - 1 else "half-space",
                    f"{result.depth_top[i]:.6g}", bottom, lit.name, it.get("confidence", ""),
                    it.get("basis", ""), it.get("notes", ""), result.run_id])
    return out.getvalue()
