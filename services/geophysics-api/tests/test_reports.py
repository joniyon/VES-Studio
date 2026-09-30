import io
from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("pygimli")
from pypdf import PdfReader

from app.inversion import InversionConfig, invert_station
from app.processing import process_dataset
from app.reports import build_report, column_figure, curve_figure, layers_csv, legend_figure, processed_csv

BENCH = Path(__file__).resolve().parents[3] / "scientific" / "benchmark-data"
INTERP = [{"lithology": "topsoil", "confidence": "medium", "basis": "b1", "notes": "n1"},
          {"lithology": "clay", "confidence": "low", "basis": "b2", "notes": ""},
          {"lithology": "fresh_basement", "confidence": "low", "basis": "b3", "notes": ""}]


@pytest.fixture(scope="module")
def chain():
    p = process_dataset(pd.read_csv(BENCH / "synthetic_schlumberger_3layer.csv"), "schlumberger")
    return p, invert_station(p, InversionConfig(n_layers=3))


def test_figures_png_and_svg(chain):
    p, r = chain
    assert curve_figure(p.table, r, "png")[:8] == b"\x89PNG\r\n\x1a\n"
    assert column_figure(r, INTERP, "png")[:8] == b"\x89PNG\r\n\x1a\n"
    svg = column_figure(r, INTERP, "svg").decode()
    assert "<svg" in svg and "Fresh basement" in svg and "pattern" in svg   # hatch patterns present
    assert legend_figure(["sand", "clay"], "png")[:4] == b"\x89PNG"
    with pytest.raises(ValueError):
        curve_figure(p.table, r, "gif")


def test_column_handles_missing_interpretation(chain):
    _, r = chain
    assert b"Unclassified" in column_figure(r, None, "svg")


def test_csv_exports(chain):
    p, r = chain
    pc = processed_csv(p)
    assert pc.startswith("# VES Studio") and "apparent_resistivity" in pc and "qc_messages" in pc
    lc = layers_csv(r, INTERP).splitlines()
    assert len(lc) == 4 and "Topsoil" in lc[1] and "half-space" in lc[3] and r.run_id in lc[1]


def test_pdf_report_contents(chain):
    p, r = chain
    pdf = build_report(project={"name": "Araromi VES Survey", "location": "Araromi, Ondo State", "researcher": "J. Arowoka"},
                       station={"id": "VES-001"}, processed=p, result=r, interpretation=INTERP,
                       geological_context="Basement complex terrain.", upload={"file_name": "x.csv", "sha256": "abc123"})
    assert pdf[:5] == b"%PDF-"
    text = "\n".join(pg.extract_text() for pg in PdfReader(io.BytesIO(pdf)).pages)
    for needle in ("Araromi VES Survey", "VES-001", "Methodology", "Data quality", "Limitations", "Conclusion",
                   "non-uniqueness".lower(), "abc123", r.run_id, "Basement complex terrain"):
        assert needle.lower() in text.lower(), needle


def test_report_states_mn_assumption():
    import numpy as np
    from app.inversion.forward import schlumberger_forward
    ab = np.array([1.5, 2, 3, 5, 7, 10, 15, 20, 30, 50, 70, 100, 150, 200.0])
    df = pd.DataFrame({"ab_half": ab, "apparent_resistivity": schlumberger_forward(ab, [100, 20, 300], [2, 10])})
    p = process_dataset(df, "schlumberger", assume_point_mn=True)
    r = invert_station(p, InversionConfig(n_layers=3))
    pdf = build_report(project={"name": "X"}, station={"id": "S"}, processed=p, result=r, interpretation=[])
    text = "\n".join(pg.extract_text() for pg in PdfReader(io.BytesIO(pdf)).pages)
    assert "point-electrode approximation" in text and "MN/2 was not supplied" in text
