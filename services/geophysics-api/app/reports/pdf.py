"""PDF report (ReportLab). Follows the scope: project, methodology, data quality, results,
interpretation, conclusion - plus limitations and a reproducibility appendix."""
import io
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app import ENGINE_VERSION
from app.arrays import get_array
from app.interpretation import get_lithology
from .figures import column_figure, curve_figure, legend_figure

_FONTS = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("Mono", str(_FONTS / "DejaVuSansMono.ttf")))
pdfmetrics.registerFont(TTFont("Mono-Bold", str(_FONTS / "DejaVuSansMono-Bold.ttf")))
pdfmetrics.registerFontFamily("Mono", normal="Mono", bold="Mono-Bold")

BODY = ParagraphStyle("body", fontName="Mono", fontSize=8.5, leading=12)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=7.5, leading=10, textColor=colors.HexColor("#555555"))
H1 = ParagraphStyle("h1", parent=BODY, fontName="Mono-Bold", fontSize=15, leading=19, spaceAfter=4)
H2 = ParagraphStyle("h2", parent=BODY, fontName="Mono-Bold", fontSize=10.5, leading=14, spaceBefore=10, spaceAfter=4, keepWithNext=1)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=7.5, leading=10)

LIMITATIONS = (
    "Non-uniqueness and equivalence: different layer models can produce nearly identical apparent-resistivity "
    "curves, so a good mathematical fit does not prove the geological model. "
    "Resolution decreases with depth. The 1D assumption requires laterally homogeneous layers. "
    "Resistivity is not a direct lithology indicator: lithology, saturation, pore-water salinity, clay content "
    "and temperature all affect it, and the ranges used for suggestions overlap."
)


def _p(text, style=BODY):
    from xml.sax.saxutils import escape
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def _kv(rows, widths=(45 * mm, 125 * mm)):
    t = Table([[_p(k, CELL), _p(v, CELL)] for k, v in rows if v not in (None, "")], colWidths=widths)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
                           ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555"))]))
    return t


def _grid(header, rows, widths):
    data = [[_p(h, CELL) for h in header]] + [[_p(c, CELL) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                           ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return t


def _fig(png: bytes, width_mm: float):
    from PIL import Image as PILImage
    w, h = PILImage.open(io.BytesIO(png)).size
    return Image(io.BytesIO(png), width=width_mm * mm, height=width_mm * mm * h / w)


def draft_summary(processed, result, interp) -> str:
    n = len(result.resistivity)
    parts = []
    for i in range(n):
        lit = get_lithology((interp[i] if i < len(interp) else {}).get("lithology") or "unclassified")
        depth = f"{result.depth_top[i]:.3g}–" + ("∞" if result.depth_bottom[i] in (None, float("inf")) else f"{result.depth_bottom[i]:.3g}")
        parts.append(f"layer {i + 1} ({depth} m) {result.resistivity[i]:.3g} Ωm"
                     + (f", interpreted as {lit.name.lower()}" if lit.id != "unclassified" else ""))
    return (f"The {n}-layer model obtained from {result.metadata['n_data']} measurements (RMS {result.rms_percent:.2f} %) "
            f"comprises: " + "; ".join(parts) + ". Interpretations are tentative and depend on local geological context.")


def build_report(*, project: dict, station: dict, processed, result, interpretation: list[dict],
                 geological_context: str = "", conclusion: str = "", upload: dict | None = None) -> bytes:
    arr = get_array(processed.lineage["array"])
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
                            title=f"VES report - {project.get('name', '')}", author=project.get("researcher", "") or "VES Studio")
    W = 170 * mm
    S = []
    S += [_p(project.get("name") or "VES interpretation report", H1),
          _p(f"Station {station.get('id', '')} · generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · VES Studio engine v{ENGINE_VERSION}", SMALL), Spacer(1, 6)]

    S += [_p("1. Project information", H2), _kv([
        ("Project", project.get("name")), ("Location", project.get("location")), ("Client / organisation", project.get("client")),
        ("Researcher", project.get("researcher")), ("Survey date", project.get("survey_date")), ("Status", project.get("status")),
        ("Description", project.get("description")), ("Notes", project.get("notes"))])]
    S += [_p("Station", H2), _kv([
        ("Station ID", station.get("id")), ("Latitude", station.get("latitude")), ("Longitude", station.get("longitude")),
        ("Elevation (m)", station.get("elevation")), ("Location description", station.get("location_description")),
        ("Survey date", station.get("survey_date")), ("Notes", station.get("notes"))])]

    S += [_p("2. Methodology", H2), _p(
        "Vertical Electrical Sounding (VES) injects current through two electrodes and measures the resulting potential "
        "difference across two others. Apparent resistivity is ρa = K · ΔV / I, where the geometric factor K follows from the "
        f"electrode geometry of the {arr.name.replace('_', '-')} array. Measured values are validated, flagged where suspect, "
        "converted to apparent resistivity, and inverted for a layered (1D) earth model."), Spacer(1, 4),
        _kv([("Array", arr.name.replace("_", "-")), ("Input units", str(processed.lineage["units"])),
             ("Array references", "; ".join(arr.references)),
             ("Inversion", f"Regularised least-squares (pyGIMLi {result.metadata.get('pygimli')}), {result.config.n_layers} layers, "
                           f"assumed data error {result.config.error_percent:g} %, λ = {result.config.lam:g}"),
             ("Engine / run", f"v{ENGINE_VERSION} · run {result.run_id}")])]

    t = processed.table
    flagged = t[t.qc_status != "PASS"]
    S += [_p("3. Data quality", H2), _p(next((i.message for i in processed.issues if i.code == "SUMMARY"), ""))]
    if len(flagged):
        by_row = {}
        for i in processed.issues:
            if i.row is not None and i.code != "SUMMARY":
                by_row.setdefault(i.row, []).append(i.message)
        S += [Spacer(1, 4), _grid(["Row", "QC", "Messages"], [[int(r.source_row), r.qc_status, " | ".join(by_row.get(int(r.source_row), []))]
              for r in flagged.itertuples()], [14 * mm, 24 * mm, 132 * mm])]
    else:
        S += [_p("No measurements were flagged.")]
    excl = processed.lineage.get("excluded_rows") or []
    if excl:
        S += [Spacer(1, 4), _p(f"Excluded from inversion by the user (values retained in the data): rows {', '.join(map(str, excl))}.")]

    S += [_p("4. Results", H2),
          _fig(curve_figure(t, result, "png", "Observed vs model apparent resistivity"), 140),
          Spacer(1, 6),
          _grid(["Layer", "ρ (Ωm)", "Thickness (m)", "Top (m)", "Bottom (m)"],
                [[i + 1, f"{result.resistivity[i]:.4g}", f"{result.thickness[i]:.4g}" if i < len(result.thickness) else "half-space",
                  f"{result.depth_top[i]:.4g}", "∞" if result.depth_bottom[i] in (None, float('inf')) else f"{result.depth_bottom[i]:.4g}"]
                 for i in range(len(result.resistivity))], [20 * mm, 30 * mm, 40 * mm, 35 * mm, 35 * mm]),
          Spacer(1, 4),
          _kv([("RMS misfit", f"{result.rms_percent:.3g} %"), ("χ²", f"{result.chi2:.3g}"), ("Iterations", result.iterations),
               ("Converged (χ² ≤ 1)", "yes" if result.converged else "no")])]

    interp = interpretation or []
    used = [get_lithology((interp[i] if i < len(interp) else {}).get("lithology") or "unclassified").id for i in range(len(result.resistivity))]
    S += [_p("5. Interpretation", H2),
          KeepTogether([_fig(column_figure(result, interp, "png"), 150),
                        _p("Legend", SMALL), _fig(legend_figure(sorted(set(used), key=used.index), "png"), 55)]),
          Spacer(1, 6),
          _grid(["Layer", "Possible lithology", "Confidence", "Basis", "Notes"],
                [[i + 1, get_lithology((interp[i] if i < len(interp) else {}).get("lithology") or "unclassified").name,
                  (interp[i] if i < len(interp) else {}).get("confidence", ""), (interp[i] if i < len(interp) else {}).get("basis", ""),
                  (interp[i] if i < len(interp) else {}).get("notes", "")] for i in range(len(result.resistivity))],
                [14 * mm, 38 * mm, 25 * mm, 51 * mm, 42 * mm])]
    if geological_context:
        S += [Spacer(1, 4), _p("Geological context", H2), _p(geological_context)]

    S += [_p("6. Limitations", H2), _p(LIMITATIONS)]
    S += [_p("7. Conclusion", H2), _p(conclusion or draft_summary(processed, result, interp))]
    if not conclusion:
        S += [_p("(Automatically drafted from the numerical results; edit before issuing.)", SMALL)]

    up = upload or {}
    S += [_p("Appendix: reproducibility", H2), _kv([
        ("Engine version", ENGINE_VERSION), ("Run ID", result.run_id), ("Backend", str(result.metadata.get("pygimli"))),
        ("Original file", up.get("file_name")), ("File SHA-256", up.get("sha256")),
        ("Column mapping", str(up.get("mapping", ""))), ("Inversion config", str(result.config))])]

    doc.build(S)
    return buf.getvalue()
