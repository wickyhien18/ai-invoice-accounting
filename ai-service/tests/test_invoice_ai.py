import json
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient  # noqa: E402

from app import llm  # noqa: E402
from app.main import app  # noqa: E402
from app.services import extractor, masking, ocr, preprocess, vendor  # noqa: E402
from app.services.fields import canonical  # noqa: E402

DATA = Path(__file__).resolve().parents[2] / "data_test"
LABELS = json.loads((DATA / "labels.json").read_text(encoding="utf-8"))
MAP = {"invoice_series": "ky_hieu", "invoice_number": "so_hoa_don", "invoice_date": "ngay_lap",
       "seller_name": "ten_nguoi_ban", "mst_seller": "mst_nguoi_ban", "total_before_tax": "tong_truoc_thue",
       "vat_rate": "thue_suat", "vat_amount": "tien_thue", "total_amount": "tong_thanh_toan"}
client = TestClient(app)


@pytest.fixture(autouse=True)
def no_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)


def pdf_ocr(id_):
    return ocr.run_ocr((DATA / "pdf" / f"{id_}.pdf").read_bytes(), f"{id_}.pdf")


# ------------------------------------------------------------------ llm.py
def test_llm_requires_key():
    with pytest.raises(llm.LLMUnavailable):
        llm.generate_json("x")


def test_llm_parses_fenced_json_and_retries(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    replies = iter(["khong phai json", '```json\n{"a": 1}\n```'])
    monkeypatch.setattr(llm, "_call_model", lambda p, m, k: next(replies))
    assert llm.generate_json("x") == {"a": 1}


def test_llm_gives_up_after_bad_json(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr(llm, "_call_model", lambda p, m, k: "[1]")
    with pytest.raises(llm.LLMError):
        llm.generate_json("x")


def test_llm_server_errors_become_unavailable(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")

    def boom(p, m, k):
        raise llm._Retryable("503")
    monkeypatch.setattr(llm, "_call_model", boom)
    with pytest.raises(llm.LLMUnavailable):
        llm.generate_json("x")


# ------------------------------------------------------------------ masking
def test_mask_roundtrip():
    text = "MST: 0487211601  STK 795761703282  email a@b.vn  Tong 4.192.668"
    masked, table = masking.mask(text)
    assert "0487211601" not in masked and "795761703282" not in masked and "a@b.vn" not in masked
    assert "4.192.668" in masked                      # so tien khong bi che
    assert masking.unmask(masked, table) == text      # khoi phuc lai dung nguyen van ban goc


# ------------------------------------------------------------------ quy tac + do tin cay
def test_rules_read_all_sample_pdfs():
    for lab in LABELS:
        r = extractor.extract_fields(pdf_ocr(lab["id"]), use_llm=False)
        for f, k in MAP.items():
            got, want = r["fields"][f]["value"], canonical(f, lab[k])
            assert (got or "").casefold() == (want or "").casefold(), (lab["id"], f, got, want)
        assert r["source"] == "rules" and r["warnings"]


def test_confidence_green_for_clean_digital_pdf():
    r = extractor.extract_fields(pdf_ocr("HD001"), use_llm=False)
    for f in ("invoice_number", "mst_seller", "invoice_date", "total_amount", "vat_amount"):
        assert r["fields"][f]["confidence"] >= 90, f


def test_llm_hallucination_gets_low_confidence(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    good = {n: {"value": None, "confidence": 99} for n in MAP}
    good.update(mst_seller={"value": "0999999999", "confidence": 99},       # khong co trong van ban
                total_amount={"value": "9999999", "confidence": 99})
    monkeypatch.setattr(llm, "generate_json", lambda prompt, schema=None: {"fields": good})
    r = extractor.extract_fields(pdf_ocr("HD001"))
    assert r["source"] == "llm"
    assert r["fields"]["mst_seller"]["confidence"] < 70
    assert r["fields"]["total_amount"]["confidence"] < 70
    assert any("khac tong" in w for w in r["warnings"])


def test_llm_prompt_is_masked_and_result_restored(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    seen = {}

    def fake(prompt, schema=None):
        seen["prompt"] = prompt
        # LLM tra lai dung token da che cho MST nguoi ban
        tok = next(t for t in ("[ID_1]", "[ID_2]", "[ID_3]") if f"Tax code): {t}" in prompt)
        return {"fields": {"mst_seller": {"value": tok, "confidence": 95}}}
    monkeypatch.setattr(llm, "generate_json", fake)
    r = extractor.extract_fields(pdf_ocr("HD001"))
    assert "0487211601" not in seen["prompt"]
    assert r["fields"]["mst_seller"]["value"] == "0487211601"


def test_llm_down_falls_back_to_rules():
    r = extractor.extract_fields(pdf_ocr("HD002"))      # khong co GEMINI_API_KEY
    assert r["source"] == "rules"
    assert any("LLM" in w for w in r["warnings"])
    assert r["fields"]["total_amount"]["value"] == str(LABELS[1]["tong_thanh_toan"])


# ------------------------------------------------------------------ OCR
def test_group_rows_joins_same_line():
    items = [ocr.Item("Tong:", 0, 100, 40, 120, 99), ocr.Item("4.192.668", 200, 102, 300, 122, 97),
             ocr.Item("Ngay", 0, 160, 40, 180, 95)]
    rows = ocr.group_rows(items)
    assert [r["text"] for r in rows] == ["Tong: 4.192.668", "Ngay"]
    assert rows[0]["confidence"] == 98.0


def test_image_goes_through_paddle_and_preprocess(monkeypatch):
    calls = {}

    def fake_items(img):
        calls["size"] = img.size
        return [ocr.Item("So (No.):", 0, 0, 80, 20, 90), ocr.Item("0291609", 100, 1, 180, 21, 80)]
    monkeypatch.setattr(ocr, "_paddle_items", fake_items)
    r = ocr.run_ocr((DATA / "images" / "HD001.png").read_bytes(), "HD001.png")
    assert r["source"] == "ocr" and r["text"] == "So (No.): 0291609"
    assert min(calls["size"]) >= preprocess.MIN_SHORT_SIDE - 2   # da phong to


def test_ocr_endpoint_503_when_paddle_missing(monkeypatch):
    def nope():
        raise ocr.OCRUnavailable("chua cai")
    monkeypatch.setattr(ocr, "_engine", nope)
    r = client.post("/ocr", files={"file": ("a.png", (DATA / "images" / "HD001.png").read_bytes())})
    assert r.status_code == 503


def test_ocr_and_extract_endpoints_with_pdf():
    pdf = (DATA / "pdf" / "HD001.pdf").read_bytes()
    r = client.post("/ocr", files={"file": ("a.pdf", pdf)})
    assert r.status_code == 200 and "4.192.668" in r.json()["data"]["text"]
    assert r.json()["data"]["source"] == "pdf_text" and "mock" not in r.json()
    r = client.post("/extract", files={"file": ("a.pdf", pdf)})
    assert r.status_code == 200
    f = r.json()["data"]["fields"]
    assert f["total_amount"]["value"] == "4192668" and f["mst_seller"]["value"] == "0487211601"


def test_extract_from_text_and_validation():
    r = client.post("/extract", data={"text": "Ký hiệu (Serial): C26MBF\nSố (No.): 0291609", "use_llm": "false"})
    assert r.json()["data"]["fields"]["invoice_series"]["value"] == "C26MBF"
    assert client.post("/extract").status_code == 422
    assert client.post("/ocr", files={"file": ("a.txt", b"hello")}).status_code == 415
    assert client.post("/ocr", files={"file": ("a.png", b"")}).status_code == 422


# ------------------------------------------------------------------ tien xu ly anh
def test_deskew_recovers_small_rotation():
    src = Image.open(DATA / "images" / "HD005.png").convert("L")
    src.thumbnail((900, 900))
    tilted = src.rotate(3, fillcolor=255)
    assert abs(preprocess._skew_angle(tilted) - (-3)) <= 1.0


# ------------------------------------------------------------------ RapidFuzz
def test_vendor_merges_variants():
    known = ["Công ty CP Vận tải Mẫu Thử Dũng", "Công ty TNHH Nội thất Mẫu Thử Tâm"]
    r = vendor.normalize_vendor("CTY CP VAN TAI MAU THU DUNG", known)
    assert r["matched"] and r["canonical"] == known[0] and r["score"] >= 95
    r = vendor.normalize_vendor("Công ty TNHH Hoàn Toàn Khác", known)
    assert not r["matched"] and r["canonical"] == "Công ty TNHH Hoàn Toàn Khác"
    assert not vendor.normalize_vendor("ABC", [])["matched"]


def test_vendor_endpoint():
    r = client.post("/normalize-vendor", json={"name": "cty tnhh noi that mau thu tam",
                                               "candidates": ["Công ty TNHH Nội thất Mẫu Thử Tâm"]})
    assert r.json()["data"]["matched"] is True


def test_engine_failure_is_cached(monkeypatch):
    monkeypatch.setattr(ocr, "_ENGINE", None)
    monkeypatch.setattr(ocr, "_FAILED", (ocr.time.time(), "mang bi chan"))
    with pytest.raises(ocr.OCRUnavailable, match="mang bi chan"):   # khong thu tai lai mo hinh
        ocr._engine()
    monkeypatch.setattr(ocr, "_FAILED", (ocr.time.time() - ocr.FAIL_TTL - 1, "cu"))
    monkeypatch.setitem(sys.modules, "paddleocr", None)            # het han -> thu lai -> import loi
    with pytest.raises(ocr.OCRUnavailable, match="Chua cai paddleocr"):
        ocr._engine()


# ------------------------------------------------------------------ quy tac chiu loi OCR (anh nhieu)
def _degrade(text, how):
    from app.services.rules import fold
    if how == "bo_dau":
        return fold(text)
    if how == "bo_dau_mat_hai_cham":
        return fold(text).replace(":", " ")
    if how == "nham_o0_l1":       # nham 0->O, 1->l trong cac so tien co dau cham
        import re
        return re.sub(r"\d{1,3}(?:\.\d{3})+", lambda m: m.group(0).replace("0", "O").replace("1", "l"), fold(text))


@pytest.mark.parametrize("how", ["bo_dau", "bo_dau_mat_hai_cham", "nham_o0_l1"])
def test_rules_survive_degraded_ocr_text(how):
    from app.services.rules import rule_extract
    from app.services.vendor import strip_accents
    for lab in LABELS:
        got = rule_extract(_degrade(pdf_ocr(lab["id"])["text"], how))
        for f, k in MAP.items():
            want = canonical(f, lab[k])
            ok = strip_accents(got[f] or "").casefold() == strip_accents(want or "").casefold()
            assert ok, (how, lab["id"], f, got[f], want)


def test_rent_item_is_not_taken_as_vat():
    from app.services.rules import rule_extract
    text = "Tiền thuê phòng họp 1 171.700 171.700\nThuế suất GTGT: 5% Tiền thuế GTGT: 73.400"
    assert rule_extract(text)["vat_amount"] == "73400"
