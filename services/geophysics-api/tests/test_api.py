import pytest
from fastapi.testclient import TestClient

pytest.importorskip("pygimli")
from app.api.main import app

c = TestClient(app)
ROWS = [{"ab_half": a, "mn_half": m, "resistance": r} for a, m, r in
        [(1.5, .5, 12.0), (3, .5, 5.6), (6, .5, 2.6), (12, 2.5, 4.5), (25, 2.5, 2.6),
         (50, 2.5, 1.5), (100, 10, 4.0), (200, 10, 2.9)]]


def test_health_and_arrays():
    assert c.get("/health").json()["status"] == "ok"
    a = c.get("/arrays").json()
    assert {x["id"] for x in a["arrays"]} >= {"schlumberger", "gradient"} and "m" in a["units"]["distance"]


def test_process_json_safe_with_errors():
    rows = ROWS + [{"ab_half": 5, "mn_half": 9, "resistance": 1}]
    r = c.post("/process", json={"array": "schlumberger", "rows": rows})
    body = r.json()
    assert r.status_code == 200 and body["has_errors"]
    assert body["rows"][-1]["apparent_resistivity"] is None and body["rows"][-1]["qc_status"] == "ERROR"


def test_invert_roundtrip():
    r = c.post("/invert", json={"array": "schlumberger", "rows": ROWS, "config": {"n_layers": 3}})
    b = r.json()
    assert r.status_code == 200 and len(b["resistivity"]) == 3 and b["depth_bottom"][-1] is None
    assert b["run_id"] and b["warnings"]


def test_bad_array_and_bad_inversion():
    assert c.post("/process", json={"array": "x", "rows": []}).status_code == 422
    r = c.post("/invert", json={"array": "wenner", "rows": [{"a": 1, "resistance": 1}] * 3})
    assert "usable measurements" in r.json()["error"]


def test_lithologies_and_suggest():
    l = c.get("/lithologies").json()
    assert any(x["id"] == "clay" for x in l["lithologies"]) and l["confidence_levels"] == ["low", "medium", "high"]
    s = c.post("/suggest-lithology", json={"layers": [{"resistivity": 20, "depth_top": 2, "depth_bottom": 12},
                                                      {"resistivity": 300, "depth_top": 12}]}).json()
    assert len(s["layers"]) == 2 and len(s["layers"][0]) > 1 and "basis" in s["layers"][0][0]


def test_exclusions_flow_through_api():
    r = c.post("/process", json={"array": "schlumberger", "rows": ROWS, "excluded_rows": [2]}).json()
    assert r["rows"][2]["qc_status"] == "EXCLUDED" and r["lineage"]["excluded_rows"] == [2]


def test_figures_exports_report():
    body = {"array": "schlumberger", "rows": ROWS, "config": {"n_layers": 3},
            "interpretation": [{"lithology": "topsoil"}, {"lithology": "clay"}, {"lithology": "fresh_basement"}]}
    assert c.post("/figures/curve", json=body).content[:4] == b"\x89PNG"
    svg = c.post("/figures/column?fmt=svg", json=body)
    assert svg.headers["content-type"] == "image/svg+xml" and b"<svg" in svg.content
    assert "layer,resistivity_ohm_m" in c.post("/export/layers.csv", json=body).text
    assert "apparent_resistivity" in c.post("/export/processed.csv", json=body).text
    pdf = c.post("/report.pdf", json={**body, "project": {"name": "P"}, "station": {"id": "S1"}})
    assert pdf.content[:5] == b"%PDF-"
    assert "summary" in c.post("/draft-summary", json=body).json()


def test_parse_xlsx(tmp_path):
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active; ws.title = "Field"
    ws.append(["AB/2", "MN/2", "R"]); ws.append([1.5, 0.5, 12.0]); ws.append([3, 0.5, 5.6])
    f = tmp_path / "d.xlsx"; wb.save(f)
    r = c.post("/parse-xlsx", files={"file": ("d.xlsx", f.read_bytes())}).json()
    assert r["headers"] == ["AB/2", "MN/2", "R"] and r["rows"][1] == ["3", "0.5", "5.6"] and r["sheets"] == ["Field"]
    assert c.post("/parse-xlsx", files={"file": ("x.xlsx", b"not a workbook")}).status_code == 422


def test_legend_endpoint():
    assert c.get("/figures/legend?ids=sand,clay").content[:4] == b"\x89PNG"
    assert c.get("/figures/legend").status_code == 200
    assert c.get("/figures/legend?ids=nope").status_code == 422


def test_working_curve_preview_and_inversion_with_working_config():
    rows = [{"ab_half": a, "apparent_resistivity": r} for a, r in
            [(1.5, 94), (2, 89), (3, 75), (5, 48), (6, 40), (6, 35), (8, 30), (12, 28), (15, 29), (15, 27), (25, 32),
             (32, 38), (40, 45), (40, 41), (50, 55), (65, 70), (80, 88), (100, 110), (100, 100), (120, 115)]]
    body = {"array": "schlumberger", "rows": rows, "assume_point_mn": True}
    w = c.post("/working-curve", json={**body, "working": {"overlap": "shift", "smooth": "median", "window": 3}}).json()
    assert len(w["spacing"]) == 16 and w["n_segments"] >= 3 and w["identity"] is False and "shifted" in w["description"]
    r = c.post("/invert", json={**body, "config": {"n_layers": 3, "working": {"overlap": "average"}}}).json()
    assert "rms_raw_percent" in r and r["working"]["n_segments"] == 1 and r["config"]["working"]["overlap"] == "average"
    bad = c.post("/working-curve", json={"array": "wenner", "rows": [{"a": 1, "apparent_resistivity": 5}] * 3,
                                         "working": {"overlap": "nope"}})
    assert bad.status_code == 422
    dd = c.post("/working-curve", json={"array": "dipole_dipole", "working": {"overlap": "average"},
                                        "rows": [{"a": 5, "n": n, "apparent_resistivity": 10.0} for n in (1, 2, 3)]}).json()
    assert "soundings only" in dd["error"]
