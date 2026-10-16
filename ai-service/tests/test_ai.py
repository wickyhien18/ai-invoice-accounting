import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

c = TestClient(app)


def test_health():
    assert c.get("/health").json() == {"status": "ok"}


def test_mock_endpoints_flagged():
    for p in ["/ocr", "/extract", "/normalize-vendor", "/classify-gl", "/classify-doc",
              "/anomaly-score", "/match-po", "/summarize"]:
        r = c.post(p)
        assert r.status_code == 200 and r.json()["mock"] is True, p
