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
    assert "Schlumberger" in r.json()["error"]
