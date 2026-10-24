"""Test Goi B (Khanh): sua truong (B2), goi y + luu but toan (B6), danh muc tai khoan / loai khoan (B7)."""
from decimal import Decimal as D

import pytest

from app.database import SessionLocal
from app.models import Account, CategoryAlias, Invoice, ItemCategory, JournalEntry
from app.services import gl_client
from app.services.invoice_data import save_extraction
from tests.conftest import login

KTV, KTT = "ktv@t.local", "ktt@t.local"
CODES = {"111": "Tiền mặt", "153": "Công cụ, dụng cụ", "211": "TSCĐ", "331": "Phải trả người bán", "1331": "Thuế GTGT",
         "6421": "Chi phí bán hàng", "6422": "Chi phí QLDN", "627": "CP sản xuất chung"}


@pytest.fixture(autouse=True)
def coa(db_setup):
    with SessionLocal() as db:
        db.add_all(Account(account_code=k, account_name=v) for k, v in CODES.items())
        db.commit()


@pytest.fixture
def H(client):
    return lambda email=KTV: login(client, email)


def make_invoice(status="cho_xac_nhan", seller="Công ty TNHH Văn phòng phẩm Mẫu Thử An", mst="0100000001",
                 before=1_000_000, rate=10, vat=100_000, total=1_100_000, conf=None):
    conf = conf or {}
    with SessionLocal() as db:
        inv = Invoice(uploaded_by=1, file_path="abc_hd.pdf", file_type="pdf", status=status)
        db.add(inv)
        db.flush()
        values = {"invoice_series": "C26TAA", "invoice_number": "0000123", "invoice_date": "15/01/2026",
                  "seller_name": seller, "mst_seller": mst, "total_before_tax": before, "vat_rate": rate,
                  "vat_amount": vat, "total_amount": total}
        save_extraction(db, inv, {k: {"value": v, "confidence": conf.get(k, 95)} for k, v in values.items()})
        db.commit()
        return inv.invoice_id


def fid(client, H, inv_id, name):
    return next(f["field_id"] for f in client.get(f"/api/invoices/{inv_id}/fields", headers=H()).json()["data"]
                if f["field_name"] == name)


def no_ai(monkeypatch, result=None):
    monkeypatch.setattr(gl_client, "classify_gl", lambda payload: result)


# ======================================================================= B2: truong
def test_fields_need_login_and_404(client, H):
    inv = make_invoice()
    assert client.get(f"/api/invoices/{inv}/fields").status_code == 401
    assert client.get("/api/invoices/999/fields", headers=H()).status_code == 404


def test_fields_levels_and_order(client, H):
    inv = make_invoice(conf={"mst_seller": 78, "total_amount": 55, "seller_name": 90, "vat_rate": 89.99})
    r = client.get(f"/api/invoices/{inv}/fields", headers=H()).json()
    by = {f["field_name"]: f for f in r["data"]}
    assert r["editable"] is True and r["status"] == "cho_xac_nhan"
    assert [f["field_name"] for f in r["data"]][:3] == ["invoice_series", "invoice_number", "invoice_date"]
    assert by["invoice_number"]["confidence_level"] == "green"
    assert by["seller_name"]["confidence_level"] == "green"          # 90 la xanh
    assert by["vat_rate"]["confidence_level"] == "yellow"            # 89.99 la vang
    assert by["mst_seller"]["confidence_level"] == "yellow" and by["total_amount"]["confidence_level"] == "red"
    assert by["total_amount"]["value"] == "1100000" and by["total_amount"]["edited"] is False


def test_missing_confidence_counts_as_red(client, H):
    inv = make_invoice()
    with SessionLocal() as db:
        from app.models import InvoiceField
        f = db.query(InvoiceField).filter_by(invoice_id=inv, field_name="vat_rate").one()
        f.confidence_score = None
        db.commit()
    by = {f["field_name"]: f for f in client.get(f"/api/invoices/{inv}/fields", headers=H()).json()["data"]}
    assert by["vat_rate"]["confidence_level"] == "red"


def test_patch_keeps_extracted_and_syncs_invoice(client, H):
    inv = make_invoice(total=1_150_000, conf={"total_amount": 50})
    f = fid(client, H, inv, "total_amount")
    r = client.patch(f"/api/invoices/{inv}/fields/{f}", json={"final_value": "1.100.000 đ"}, headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["data"]["extracted_value"] == "1150000" and d["data"]["final_value"] == "1100000"
    assert d["data"]["edited"] is True and d["data"]["confidence_level"] == "red"   # diem may khong doi khi nguoi sua
    assert D(d["invoice"]["total_amount"]) == 1_100_000
    assert d["checks"]["total_matches"] is True                                     # sua xong thi tong tien khop
    with SessionLocal() as db:
        assert db.get(Invoice, inv).total_amount == D("1100000")


def test_patch_same_value_confirms_and_null_reverts(client, H):
    inv = make_invoice(conf={"seller_name": 60})
    f = fid(client, H, inv, "seller_name")
    d = client.patch(f"/api/invoices/{inv}/fields/{f}", json={"final_value": "Công ty TNHH Văn phòng phẩm Mẫu Thử An"},
                     headers=H()).json()["data"]
    assert d["confirmed"] is True and d["edited"] is False
    d = client.patch(f"/api/invoices/{inv}/fields/{f}", json={"final_value": None}, headers=H()).json()["data"]
    assert d["confirmed"] is False and d["final_value"] is None
    d = client.patch(f"/api/invoices/{inv}/fields/{f}", json={"final_value": "   "}, headers=H()).json()["data"]
    assert d["final_value"] is None


def test_patch_normalizes_and_validates(client, H):
    inv = make_invoice()
    n = lambda name: fid(client, H, inv, name)  # noqa: E731
    url = lambda name: f"/api/invoices/{inv}/fields/{n(name)}"  # noqa: E731
    assert client.patch(url("invoice_date"), json={"final_value": "01-02-2026"}, headers=H()).json()["data"]["final_value"] == "2026-02-01"
    assert client.patch(url("mst_seller"), json={"final_value": "0100 000 002"}, headers=H()).json()["data"]["final_value"] == "0100000002"
    assert client.patch(url("invoice_number"), json={"final_value": "45"}, headers=H()).json()["data"]["final_value"] == "0000045"
    assert client.patch(url("vat_rate"), json={"final_value": "8%"}, headers=H()).json()["data"]["final_value"] == "8"
    for name, bad in [("invoice_date", "ngày mai"), ("total_amount", "abc"), ("vat_rate", "tám"), ("mst_seller", "chưa có")]:
        r = client.patch(url(name), json={"final_value": bad}, headers=H())
        assert r.status_code == 422, name
    assert client.patch(url("invoice_series"), json={"final_value": "ABCDEFGHIJK"}, headers=H()).status_code == 422
    with SessionLocal() as db:   # gia tri hong khong lam ban cot invoices
        assert str(db.get(Invoice, inv).invoice_date) == "2026-02-01"


def test_patch_locked_after_submit_and_wrong_invoice(client, H):
    for st in ("cho_duyet", "da_duyet"):
        inv = make_invoice(status=st)
        f = fid(client, H, inv, "total_amount")
        assert client.patch(f"/api/invoices/{inv}/fields/{f}", json={"final_value": "1"}, headers=H()).status_code == 409
        assert client.get(f"/api/invoices/{inv}/fields", headers=H()).json()["editable"] is False
    a, b = make_invoice(), make_invoice()
    f = fid(client, H, a, "total_amount")
    assert client.patch(f"/api/invoices/{b}/fields/{f}", json={"final_value": "1"}, headers=H()).status_code == 404
    rej = make_invoice(status="tu_choi")     # bi tu choi thi sua lai duoc de gui duyet lan nua
    f = fid(client, H, rej, "total_amount")
    assert client.patch(f"/api/invoices/{rej}/fields/{f}", json={"final_value": "1"}, headers=H()).status_code == 200


# ======================================================================= B6: goi y
def test_suggest_needs_login_and_state(client, H, monkeypatch):
    no_ai(monkeypatch)
    inv = make_invoice()
    assert client.post(f"/api/invoices/{inv}/suggest-entries").status_code == 401
    assert client.post("/api/invoices/999/suggest-entries", headers=H()).status_code == 404
    assert client.post(f"/api/invoices/{make_invoice(status='dang_xu_ly')}/suggest-entries", headers=H()).status_code == 409


def test_suggest_ml_gives_main_line_plus_vat_line(client, H, monkeypatch):
    seen = []
    monkeypatch.setattr(gl_client, "classify_gl", lambda p: seen.append(p) or
                        {"debit_account": "153", "credit_account": "331", "probability": 0.8, "source": "ml"})
    inv = make_invoice()
    r = client.post(f"/api/invoices/{inv}/suggest-entries", headers=H()).json()
    main, vat = r["data"]
    assert (main["debit_account"], main["credit_account"], main["amount"], main["source"]) == ("153", "331", "1000000.00", "ml")
    assert main["probability"] == 0.8
    assert (vat["debit_account"], vat["credit_account"], vat["amount"], vat["source"]) == ("1331", "331", "100000.00", "rule")
    assert seen[0]["use_llm"] is True and seen[0]["total_before_tax"] == 1_000_000
    assert "1331" not in {a["code"] for a in seen[0]["accounts"]} and "153" in {a["code"] for a in seen[0]["accounts"]}
    assert "mst_seller" not in seen[0]                                 # khong gui MST ra ngoai


def test_suggest_llm_source_is_labelled(client, H, monkeypatch):
    no_ai(monkeypatch, {"debit_account": "6421", "credit_account": "331", "probability": None, "source": "llm", "reason": "van chuyen"})
    d = client.post(f"/api/invoices/{make_invoice()}/suggest-entries", headers=H()).json()["data"][0]
    assert d["source"] == "llm" and "Gemini" in d["note"] and "van chuyen" in d["note"]


def test_suggest_ai_down_falls_back_to_default_with_warning(client, H, monkeypatch):
    no_ai(monkeypatch, None)
    r = client.post(f"/api/invoices/{make_invoice()}/suggest-entries", headers=H()).json()
    assert r["data"][0]["source"] == "rule" and r["data"][0]["debit_account"] == "6422"
    assert any("AI" in w for w in r["warnings"])


def test_suggest_ignores_account_not_in_chart(client, H, monkeypatch):
    no_ai(monkeypatch, {"debit_account": "999", "credit_account": "331", "probability": 0.9, "source": "ml"})
    r = client.post(f"/api/invoices/{make_invoice()}/suggest-entries", headers=H()).json()
    assert r["data"][0]["source"] == "rule" and r["warnings"]


def test_suggest_history_beats_ml(client, H, monkeypatch):
    monkeypatch.setattr(gl_client, "classify_gl", lambda p: pytest.fail("co lich su thi khong can goi AI"))
    for acct in ("627", "627", "6421"):    # 2/3 lan truoc dung 627
        old = make_invoice(status="da_duyet", mst="0100000009", seller="NCC cu")
        with SessionLocal() as db:
            db.add_all([JournalEntry(invoice_id=old, debit_account=acct, credit_account="331", amount=D("1000000")),
                        JournalEntry(invoice_id=old, debit_account="1331", credit_account="331", amount=D("100000"))])
            db.commit()
    draft = make_invoice(mst="0100000009", seller="NCC cu")   # nhap khong tinh vao lich su
    with SessionLocal() as db:
        db.add(JournalEntry(invoice_id=draft, debit_account="153", credit_account="331", amount=D("1")))
        db.commit()
    new = make_invoice(mst="0100000009", seller="Ten da doi khac")
    d = client.post(f"/api/invoices/{new}/suggest-entries", headers=H()).json()["data"][0]
    assert d["source"] == "history" and d["debit_account"] == "627" and d["probability"] == pytest.approx(0.6667, abs=1e-3)


def test_suggest_alias_matches_without_diacritics(client, H, monkeypatch):
    monkeypatch.setattr(gl_client, "classify_gl", lambda p: pytest.fail("alias thi khong can goi AI"))
    with SessionLocal() as db:
        c = ItemCategory(category_name="Công cụ dụng cụ", default_debit_account="153")
        db.add(c)
        db.flush()
        db.add(CategoryAlias(alias_text="Thiết bị văn phòng", category_id=c.category_id))
        db.commit()
    inv = make_invoice(seller="CONG TY TNHH THIET BI VAN PHONG ABC", mst="0100000077")
    d = client.post(f"/api/invoices/{inv}/suggest-entries", headers=H()).json()["data"][0]
    assert d["source"] == "alias" and d["debit_account"] == "153" and d["credit_account"] == "331"
    other = make_invoice(seller="Cong ty thiet bi van phong phan phoi", mst="0100000078")  # chua du cum tu 'phong' khong lien tuc
    assert client.post(f"/api/invoices/{other}/suggest-entries", headers=H()).json()["data"][0]["source"] == "alias"


def test_suggest_without_vat_or_without_amounts(client, H, monkeypatch):
    no_ai(monkeypatch, {"debit_account": "153", "credit_account": "331", "probability": 0.7, "source": "ml"})
    inv = make_invoice(vat=0, rate=0, total=1_000_000)
    assert len(client.post(f"/api/invoices/{inv}/suggest-entries", headers=H()).json()["data"]) == 1
    bare = make_invoice(before=None, rate=None, vat=None, total=None)
    r = client.post(f"/api/invoices/{bare}/suggest-entries", headers=H())
    assert r.status_code == 422 and "số tiền" in r.json()["detail"]
    only_total = make_invoice(before=None, vat=None, total=1_100_000)    # chi co tong: coi la khong thue
    d = client.post(f"/api/invoices/{only_total}/suggest-entries", headers=H()).json()["data"]
    assert d[0]["amount"] == "1100000.00" and len(d) == 1


def test_suggest_warns_when_totals_disagree(client, H, monkeypatch):
    no_ai(monkeypatch, {"debit_account": "153", "credit_account": "331", "probability": 0.7, "source": "ml"})
    inv = make_invoice(total=1_500_000)
    assert client.post(f"/api/invoices/{inv}/suggest-entries", headers=H()).json()["warnings"]


# ======================================================================= B6: luu
def body(*lines):
    return {"entries": [{"debit_account": d, "credit_account": c, "amount": a} for d, c, a in lines]}


def test_put_replaces_not_appends(client, H):
    inv = make_invoice()
    u = f"/api/invoices/{inv}/journal-entries"
    r = client.put(u, json=body(("153", "331", "1000000"), ("1331", "331", "100000.00")), headers=H())
    assert r.status_code == 200 and len(r.json()["data"]) == 2 and r.json()["warnings"] == []
    client.put(u, json=body(("6422", "111", "1100000")), headers=H())
    rows = client.get(u, headers=H()).json()["data"]
    assert [(e["debit_account"], e["credit_account"], e["amount"]) for e in rows] == [("6422", "111", "1100000.00")]


def test_put_validation(client, H):
    inv = make_invoice()
    u = f"/api/invoices/{inv}/journal-entries"
    cases = [body(("153", "153", "1")), body(("153", "331", "0")), body(("153", "331", "-5")), body(("153", "331", "1.234")),
             body(("153", "331", "abc")), body(("153", "331", "NaN")), body(("153", "331", "1e30")),
             body(("999", "331", "1")), {"entries": []}, {}]
    for c in cases:
        assert client.put(u, json=c, headers=H()).status_code == 422, c
    assert client.get(u, headers=H()).json()["data"] == []                    # loi thi khong luu gi
    too_many = body(*[("153", "331", "1")] * 21)
    assert client.put(u, json=too_many, headers=H()).status_code == 422
    assert client.put(u, json=body(("153", "331", "1")), headers=None).status_code == 401


def test_put_warns_when_sum_differs_and_locked_states(client, H):
    inv = make_invoice()
    r = client.put(f"/api/invoices/{inv}/journal-entries", json=body(("153", "331", "5")), headers=H())
    assert r.status_code == 200 and r.json()["warnings"]
    for st in ("cho_duyet", "da_duyet"):
        locked = make_invoice(status=st)
        assert client.put(f"/api/invoices/{locked}/journal-entries", json=body(("153", "331", "1")), headers=H()).status_code == 409
    assert client.put("/api/invoices/999/journal-entries", json=body(("153", "331", "1")), headers=H()).status_code == 404


def test_saved_entries_are_decimal_exact(client, H):
    inv = make_invoice()
    client.put(f"/api/invoices/{inv}/journal-entries", json=body(("153", "331", "0.10"), ("1331", "331", "0.20")), headers=H())
    with SessionLocal() as db:
        assert sum(e.amount for e in db.query(JournalEntry).filter_by(invoice_id=inv)) == D("0.30")


# ======================================================================= B7: danh muc
def test_catalog_read_ok_write_needs_ktt(client, H):
    assert client.get("/api/accounts").status_code == 401
    assert len(client.get("/api/accounts", headers=H()).json()["data"]) == len(CODES)
    assert client.post("/api/accounts", json={"account_code": "999", "account_name": "x"}, headers=H()).status_code == 403
    assert client.post("/api/categories", json={"category_name": "x"}, headers=H()).status_code == 403
    assert client.delete("/api/accounts/111", headers=H()).status_code == 403


def test_accounts_crud_and_search(client, H):
    k = H(KTT)
    assert client.post("/api/accounts", json={"account_code": "642", "account_name": "CP QLKD"}, headers=k).status_code == 201
    assert client.post("/api/accounts", json={"account_code": "642", "account_name": "trùng"}, headers=k).status_code == 409
    for bad in ("12", "abc", "12345678901", ""):
        assert client.post("/api/accounts", json={"account_code": bad, "account_name": "x"}, headers=k).status_code == 422
    assert client.post("/api/accounts", json={"account_code": "643", "account_name": "  "}, headers=k).status_code == 422
    assert client.put("/api/accounts/642", json={"account_name": "Chi phí QLKD"}, headers=k).json()["data"]["account_name"] == "Chi phí QLKD"
    assert client.put("/api/accounts/000", json={"account_name": "x"}, headers=k).status_code == 404
    assert [a["account_code"] for a in client.get("/api/accounts?q=chi phi", headers=k).json()["data"]] == ["642", "6421", "6422"]
    assert client.delete("/api/accounts/642", headers=k).status_code == 200
    assert client.delete("/api/accounts/642", headers=k).status_code == 404


def test_cannot_delete_account_in_use(client, H):
    k = H(KTT)
    inv = make_invoice()
    client.put(f"/api/invoices/{inv}/journal-entries", json=body(("153", "331", "1")), headers=k)
    assert client.delete("/api/accounts/153", headers=k).status_code == 409
    c = client.post("/api/categories", json={"category_name": "Điện nước", "default_debit_account": "627"}, headers=k).json()["data"]
    assert client.delete("/api/accounts/627", headers=k).status_code == 409
    client.delete(f"/api/categories/{c['category_id']}", headers=k)
    assert client.delete("/api/accounts/627", headers=k).status_code == 200


def test_categories_and_aliases(client, H):
    k = H(KTT)
    c = client.post("/api/categories", json={"category_name": " Văn  phòng phẩm ", "default_debit_account": "6422"}, headers=k)
    assert c.status_code == 201 and c.json()["data"]["category_name"] == "Văn phòng phẩm"
    cid = c.json()["data"]["category_id"]
    assert client.post("/api/categories", json={"category_name": "Văn phòng phẩm"}, headers=k).status_code == 409
    assert client.post("/api/categories", json={"category_name": "A", "default_debit_account": "000"}, headers=k).status_code == 422
    assert client.post(f"/api/categories/{cid}/aliases", json={"alias_text": "bút giấy"}, headers=k).status_code == 201
    dup = client.post(f"/api/categories/{cid}/aliases", json={"alias_text": "BUT GIAY"}, headers=k)
    assert dup.status_code == 409
    assert client.post(f"/api/categories/{cid}/aliases", json={"alias_text": "!"}, headers=k).status_code == 422
    assert client.post("/api/categories/999/aliases", json={"alias_text": "abc"}, headers=k).status_code == 404
    got = client.get("/api/categories", headers=H()).json()["data"][0]
    assert got["default_debit_account"] == "6422" and [a["alias_text"] for a in got["aliases"]] == ["bút giấy"]
    upd = client.put(f"/api/categories/{cid}", json={"category_name": "VPP", "default_debit_account": None}, headers=k)
    assert upd.json()["data"]["default_debit_account"] is None
    aid = got["aliases"][0]["alias_id"]
    assert client.delete(f"/api/categories/999/aliases/{aid}", headers=k).status_code == 404
    assert client.delete(f"/api/categories/{cid}/aliases/{aid}", headers=k).status_code == 200
    assert client.delete(f"/api/categories/{cid}", headers=k).status_code == 200
    assert client.get("/api/categories", headers=k).json()["data"] == []


def test_cannot_delete_category_linked_to_fields(client, H):
    k = H(KTT)
    inv = make_invoice()
    cid = client.post("/api/categories", json={"category_name": "X"}, headers=k).json()["data"]["category_id"]
    with SessionLocal() as db:
        from app.models import InvoiceField
        db.query(InvoiceField).filter_by(invoice_id=inv, field_name="seller_name").one().category_id = cid
        db.commit()
    assert client.delete(f"/api/categories/{cid}", headers=k).status_code == 409
