import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

c = TestClient(app)


def test_health():
    d = c.get("/health").json()
    assert d["status"] == "ok" and "ocr_ready" in d


def test_only_unfinished_endpoints_are_mock():
    r = c.post("/summarize")
    assert r.status_code == 200 and r.json()["mock"] is True


def test_real_endpoints_are_not_shadowed_by_mock():
    """Mock dang ky truoc se de len endpoint that (tung xay ra voi /anomaly-score va /match-po)."""
    rows = [{"invoice_id": i, "seller_name": f"NCC {i}", "total_amount": 1_000_000 + i} for i in range(1, 6)]
    r = c.post("/anomaly-score", json=rows)
    assert r.status_code == 200 and isinstance(r.json(), list) and "mock" not in str(r.json())
    r = c.post("/match-po", json={"seller_name": "", "candidates": []})
    assert r.status_code == 200 and r.json()["best_po_id"] is None
    assert c.post("/classify-gl").status_code == 422  # thieu body, khong phai mock 200
