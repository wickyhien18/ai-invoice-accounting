import json
from pathlib import Path

import pytest

from app.services import ai_client
from tests.conftest import login

DATA = Path(__file__).resolve().parents[2] / "data_test"
LABELS = {l["id"]: l for l in json.loads((DATA / "labels.json").read_text(encoding="utf-8"))}
from decimal import Decimal as D  # noqa: E402

H = lambda c, e="ktv@t.local": login(c, e)  # noqa: E731


def up(client, name, content, headers=None):
    return client.post("/api/invoices", files={"file": (name, content)}, headers=headers or H(client))


def xml_bytes(id_="HD001"):
    return (DATA / "xml" / f"{id_}.xml").read_bytes()


def test_upload_requires_login(client):
    assert client.post("/api/invoices", files={"file": ("a.xml", b"<HDon/>")}).status_code == 401
    assert client.get("/api/invoices").status_code == 401
    assert client.get("/api/invoices/1/file").status_code == 401


def test_upload_xml_extracts_directly_without_ai(client, monkeypatch):
    monkeypatch.setattr(ai_client, "extract_invoice", lambda *a: pytest.fail("XML khong duoc goi AI"))
    r = up(client, "hd.xml", xml_bytes())
    assert r.status_code == 201
    d = r.json()["data"]
    lab = LABELS["HD001"]
    assert d["status"] == "cho_xac_nhan" and d["file_type"] == "xml" and d["filename"] == "hd.xml"
    assert d["invoice_number"] == lab["so_hoa_don"] and d["invoice_series"] == lab["ky_hieu"]
    assert d["invoice_date"] == "2026-06-23" and d["mst_seller"] == lab["mst_nguoi_ban"]
    assert D(d["total_amount"]) == 4192668 and D(d["vat_rate"]) == 8 and D(d["vat_amount"]) == 310568


def test_all_sample_xml_match_labels(client):
    for id_, lab in LABELS.items():
        p = DATA / "xml" / f"{id_}.xml"
        d = up(client, p.name, p.read_bytes()).json()["data"]
        assert d["invoice_number"] == lab["so_hoa_don"], id_
        assert d["mst_seller"] == lab["mst_nguoi_ban"], id_
        assert D(d["total_amount"]) == lab["tong_thanh_toan"], id_
        assert D(d["total_before_tax"]) == lab["tong_truoc_thue"], id_
        assert D(d["vat_rate"]) == lab["thue_suat"], id_
        assert d["seller_name"] == lab["ten_nguoi_ban"], id_


def test_upload_pdf_runs_ai_in_background(client, monkeypatch):
    fake = {"fields": {"invoice_number": {"value": "123", "confidence": 88},
                       "total_amount": {"value": "1.100.000", "confidence": 55}}}
    monkeypatch.setattr(ai_client, "extract_invoice", lambda path, name: fake)
    r = up(client, "a.pdf", (DATA / "pdf" / "HD001.pdf").read_bytes())
    assert r.status_code == 201
    got = client.get(f"/api/invoices/{r.json()['data']['invoice_id']}", headers=H(client)).json()["data"]
    assert got["status"] == "cho_xac_nhan"
    assert got["invoice_number"] == "0000123" and D(got["total_amount"]) == 1100000


def test_ai_down_marks_loi_xu_ly_then_reprocess(client, monkeypatch):
    def boom(*a):
        raise ai_client.AIServiceError("tat")
    monkeypatch.setattr(ai_client, "extract_invoice", boom)
    iid = up(client, "a.png", (DATA / "images" / "HD001.png").read_bytes()).json()["data"]["invoice_id"]
    assert client.get(f"/api/invoices/{iid}", headers=H(client)).json()["data"]["status"] == "loi_xu_ly"
    monkeypatch.setattr(ai_client, "extract_invoice",
                        lambda *a: {"fields": {"invoice_number": {"value": "9", "confidence": 90}}})
    assert client.post(f"/api/invoices/{iid}/reprocess", headers=H(client)).status_code == 200
    assert client.get(f"/api/invoices/{iid}", headers=H(client)).json()["data"]["status"] == "cho_xac_nhan"


def test_upload_rejects_bad_files(client):
    assert up(client, "a.exe", b"MZ").status_code == 415
    assert up(client, "a.pdf", b"not a pdf").status_code == 415           # sai chu ky file
    assert up(client, "a.xml", b"<html></html>").status_code == 422        # khong phai HDon
    assert up(client, "a.xml", b"<HDon><x></HDon>").status_code == 422     # XML hong
    assert up(client, "a.pdf", b"%PDF" + b"0" * (10 * 1024 * 1024)).status_code == 413


def test_xml_xxe_is_blocked(client):
    evil = b'<?xml version="1.0"?><!DOCTYPE HDon [<!ENTITY x SYSTEM "file:///etc/passwd">]><HDon>&x;</HDon>'
    assert up(client, "evil.xml", evil).status_code == 422


def test_list_filter_and_detail_and_file(client):
    up(client, "a.xml", xml_bytes("HD001"))
    up(client, "b.xml", xml_bytes("HD002"))
    h = H(client)
    all_ = client.get("/api/invoices", headers=h).json()
    assert all_["total"] == 2 and all_["data"][0]["filename"] == "b.xml"   # moi nhat truoc
    assert client.get("/api/invoices?q=" + LABELS["HD002"]["so_hoa_don"], headers=h).json()["total"] == 1
    assert client.get("/api/invoices?status=cho_duyet", headers=h).json()["total"] == 0
    assert client.get("/api/invoices?date_from=bad", headers=h).status_code == 422
    assert client.get("/api/invoices/999", headers=h).status_code == 404
    f = client.get("/api/invoices/1/file", headers=h)
    assert f.status_code == 200 and f.content == xml_bytes("HD001")


def test_check_ok_and_duplicate(client, monkeypatch):
    monkeypatch.setattr(ai_client, "normalize_vendor", lambda *a: None)
    up(client, "a.xml", xml_bytes("HD001"))
    h = H(client)
    c = client.post("/api/invoices/1/check", headers=h).json()["data"]
    assert c["mst_valid"] is True and c["total_matches"] is True and c["duplicate"] is False
    up(client, "again.xml", xml_bytes("HD001"))
    c = client.post("/api/invoices/2/check", headers=h).json()["data"]
    assert c["duplicate"] is True and c["duplicate_of"] == [1]


def test_check_detects_bad_mst_and_total(client, monkeypatch):
    monkeypatch.setattr(ai_client, "normalize_vendor", lambda *a: None)
    bad = xml_bytes("HD001").replace(b"<MST>0487211601</MST>", b"<MST>12345</MST>") \
                            .replace(b"<TgTTTBSo>4192668</TgTTTBSo>", b"<TgTTTBSo>4192000</TgTTTBSo>")
    up(client, "bad.xml", bad)
    c = client.post("/api/invoices/1/check", headers=H(client)).json()["data"]
    assert c["mst_valid"] is False and c["total_matches"] is False and len(c["issues"]) >= 2


def test_vendor_suggestion(client, monkeypatch):
    up(client, "a.xml", xml_bytes("HD001"))
    renamed = xml_bytes("HD001").replace(b"<SHDon>291609</SHDon>", b"<SHDon>1</SHDon>") \
        .replace("Công ty CP Vận tải Mẫu Thử Dũng".encode(), "CTY CP VAN TAI MAU THU DUNG".encode())
    up(client, "b.xml", renamed)
    monkeypatch.setattr(ai_client, "normalize_vendor", lambda name, cands: {
        "canonical": cands[0], "score": 96.0, "matched": True})
    c = client.post("/api/invoices/2/check", headers=H(client)).json()["data"]
    assert c["vendor_suggestion"]["canonical"] == "Công ty CP Vận tải Mẫu Thử Dũng"


def test_progress_endpoint(client, monkeypatch):
    monkeypatch.setattr(ai_client, "extract_invoice", lambda path, name: {"fields": {}})
    inv = up(client, "a.pdf", (DATA / "pdf" / "HD001.pdf").read_bytes()).json()["data"]
    # da xu ly xong -> 100%
    p = client.get(f"/api/invoices/{inv['invoice_id']}/progress", headers=H(client)).json()["data"]
    assert p["percent"] == 100 and p["status"] == "cho_xac_nhan"
    # dang xu ly: lay tien do tu ai-service; ai-service khong tra loi -> van co gia tri du phong
    from app.database import SessionLocal
    from app.models import Invoice
    with SessionLocal() as db:
        db.get(Invoice, inv["invoice_id"]).status = "dang_xu_ly"
        db.commit()
    monkeypatch.setattr(ai_client, "get_progress", lambda job: {"percent": 55, "stage": "Đang trích xuất"})
    p = client.get(f"/api/invoices/{inv['invoice_id']}/progress", headers=H(client)).json()["data"]
    assert (p["status"], p["percent"]) == ("dang_xu_ly", 55)
    monkeypatch.setattr(ai_client, "get_progress", lambda job: None)
    assert client.get(f"/api/invoices/{inv['invoice_id']}/progress", headers=H(client)).json()["data"]["percent"] == 5
    assert client.get("/api/invoices/999999/progress", headers=H(client)).status_code == 404
    assert client.get(f"/api/invoices/{inv['invoice_id']}/progress").status_code == 401


def test_unexpected_error_marks_loi_xu_ly_not_stuck(client, monkeypatch):
    """Loi bat ngo (khong nam trong danh sach loi quen thuoc) van phai ra loi_xu_ly, khong ket 'dang_xu_ly'."""
    def boom(path, name):
        raise ValueError("loi bat ngo")
    monkeypatch.setattr(ai_client, "extract_invoice", boom)
    inv = up(client, "a.pdf", (DATA / "pdf" / "HD001.pdf").read_bytes()).json()["data"]
    assert client.get(f"/api/invoices/{inv['invoice_id']}", headers=H(client)).json()["data"]["status"] == "loi_xu_ly"


def test_background_jobs_run_one_at_a_time(monkeypatch):
    """Nhieu hoa don PDF/anh cung luc: ai-service chi nhan mot yeu cau moi lan."""
    import threading
    import time
    from app.database import SessionLocal
    from app.models import Invoice
    from app.services.invoice_data import run_in_background
    with SessionLocal() as db:
        ids = []
        for n in range(4):
            inv = Invoice(uploaded_by=1, file_path=f"x{n}_a.pdf", file_type="pdf", status="dang_xu_ly")
            db.add(inv)
            db.commit()
            ids.append(inv.invoice_id)
    state = {"now": 0, "max": 0}
    guard = threading.Lock()

    def slow(path, name):
        with guard:
            state["now"] += 1
            state["max"] = max(state["max"], state["now"])
        time.sleep(0.05)
        with guard:
            state["now"] -= 1
        return {"fields": {}}
    monkeypatch.setattr(ai_client, "extract_invoice", slow)
    ts = [threading.Thread(target=run_in_background, args=(i,)) for i in ids]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert state["max"] == 1
    with SessionLocal() as db:
        assert {db.get(Invoice, i).status for i in ids} == {"cho_xac_nhan"}   # ca 4 deu xong


def test_recover_stuck_reprocesses_invoices_left_processing(monkeypatch):
    from app.database import SessionLocal
    from app.models import Invoice
    from app.services.invoice_data import recover_stuck
    with SessionLocal() as db:
        a = Invoice(uploaded_by=1, file_path="x1_a.pdf", file_type="pdf", status="dang_xu_ly")
        b = Invoice(uploaded_by=1, file_path="x2_b.pdf", file_type="pdf", status="da_duyet")
        db.add_all([a, b])
        db.commit()
        ia, ib = a.invoice_id, b.invoice_id
    monkeypatch.setattr(ai_client, "extract_invoice", lambda path, name: {"fields": {}})
    assert recover_stuck() == 1
    with SessionLocal() as db:
        assert db.get(Invoice, ia).status == "cho_xac_nhan" and db.get(Invoice, ib).status == "da_duyet"
