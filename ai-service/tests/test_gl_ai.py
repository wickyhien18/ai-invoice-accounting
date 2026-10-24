"""Test Goi B o ai-service: mo hinh dinh khoan (B5), Gemini du phong cho nguoi ban moi (B6), phan loai chung tu (B8)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import llm  # noqa: E402
from app.main import app  # noqa: E402
from app.services import gl_model  # noqa: E402

c = TestClient(app)
ACCOUNTS = [{"code": x, "name": f"TK {x}"} for x in ("153", "211", "331", "6421", "6422", "111")]
LOW = {"debit_account": "6422", "credit_account": "331", "debit_probability": 0.4, "credit_probability": 0.9,
       "probability": 0.36, "alternatives": []}


def post(**kw):
    body = {"seller_name": "Công ty TNHH Thiết bị IT Mẫu Thử Quang", "vat_rate": 10, "total_before_tax": 45_000_000, **kw}
    return c.post("/classify-gl", json=body)


def test_make_text_ignores_accents_and_buckets_amount():
    a = gl_model.make_text("Công ty TNHH Văn phòng phẩm Hà", 8, 2_000_000)
    b = gl_model.make_text("CONG TY TNHH VAN PHONG PHAM HA", "8", "2000000")
    assert a == b and "amt_1" in a.split() and "vat_8" in a.split()


def test_big_it_purchase_is_fixed_asset_small_is_tool():
    big = post().json()["data"]
    small = post(total_before_tax=4_000_000).json()["data"]
    assert big["debit_account"] == "211" and big["credit_account"] == "331" and big["source"] == "ml"
    assert small["debit_account"] == "153"
    assert 0 < big["probability"] <= 1


def test_missing_fields_do_not_crash():
    r = c.post("/classify-gl", json={})
    assert r.status_code == 200 and r.json()["data"]["debit_account"]


def test_llm_used_only_when_new_vendor_and_ml_unsure(monkeypatch):
    calls = []
    monkeypatch.setattr(gl_model, "predict", lambda *a, **k: dict(LOW))
    monkeypatch.setattr(llm, "generate_json", lambda p, s=None: calls.append(p) or
                        {"debit_account": "6421", "credit_account": "331", "reason": "ban hang"})
    assert post().json()["data"]["source"] == "ml" and not calls              # use_llm tat
    assert post(use_llm=True).json()["data"]["source"] == "ml" and not calls  # khong co danh muc tai khoan
    d = post(use_llm=True, accounts=ACCOUNTS).json()["data"]
    assert d["source"] == "llm" and d["debit_account"] == "6421" and d["probability"] is None
    assert d["ml_suggestion"]["debit_account"] == "6422" and len(calls) == 1


def test_llm_not_called_when_ml_confident(monkeypatch):
    monkeypatch.setattr(llm, "generate_json", lambda *a, **k: pytest.fail("khong duoc goi Gemini"))
    monkeypatch.setattr(gl_model, "predict", lambda *a, **k: {**LOW, "probability": 0.9})
    assert post(use_llm=True, accounts=ACCOUNTS).json()["data"]["source"] == "ml"


def test_llm_answer_outside_chart_is_rejected(monkeypatch):
    monkeypatch.setattr(gl_model, "predict", lambda *a, **k: dict(LOW))
    monkeypatch.setattr(llm, "generate_json", lambda *a, **k: {"debit_account": "999", "credit_account": "331"})
    d = post(use_llm=True, accounts=ACCOUNTS).json()["data"]
    assert d["source"] == "ml" and "999" in d["llm_error"]


def test_llm_unavailable_falls_back_to_ml(monkeypatch):
    def boom(*a, **k):
        raise llm.LLMUnavailable("het han muc")
    monkeypatch.setattr(gl_model, "predict", lambda *a, **k: dict(LOW))
    monkeypatch.setattr(llm, "generate_json", boom)
    d = post(use_llm=True, accounts=ACCOUNTS).json()["data"]
    assert d["source"] == "ml" and d["debit_account"] == "6422" and "het han muc" in d["llm_error"]


def test_llm_prompt_masks_ids(monkeypatch):
    seen = []
    monkeypatch.setattr(gl_model, "predict", lambda *a, **k: dict(LOW))
    monkeypatch.setattr(llm, "generate_json", lambda p, s=None: seen.append(p) or
                        {"debit_account": "6422", "credit_account": "331", "reason": ""})
    post(use_llm=True, accounts=ACCOUNTS, seller_name="Cong ty ABC lien he 0912345678")
    assert "0912345678" not in seen[0]


def test_classify_doc_known_types_and_garbage():
    r = c.post("/classify-doc", json={"text": "HÓA ĐƠN GIÁ TRỊ GIA TĂNG\nKý hiệu: C26TAA\nThuế suất GTGT: 10%"}).json()["data"]
    assert r["doc_type"] == "hoa_don_gtgt" and not r["can_xem_lai"]
    r = c.post("/classify-doc", json={"text": "PHIEU XUAT KHO so 000123 Thu kho"}).json()["data"]
    assert r["doc_type"] == "phieu_giao_hang_xuat_kho"
    assert c.post("/classify-doc", json={"text": "   "}).status_code == 422
    assert c.post("/classify-doc", json={"text": "zzzz qqqq xxxx"}).json()["data"]["probability"] < 1
