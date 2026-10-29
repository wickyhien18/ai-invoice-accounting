"""Phan quyen: KTV chi lam viec cua KTV, KTT chi lam viec cua KTT; xoa hoa don chi KTT va phai nhap lai mat khau."""
from pathlib import Path

from app.config import settings
from app.database import SessionLocal
from app.models import Invoice, InvoiceField
from tests.conftest import login

DATA = Path(__file__).resolve().parents[2] / "data_test"
KTV, KTT = "ktv@t.local", "ktt@t.local"
PW = "pw123456"


def upload_xml(client):
    r = client.post("/api/invoices", files={"file": ("hd.xml", (DATA / "xml" / "HD001.xml").read_bytes())},
                    headers=login(client, KTV))
    assert r.status_code == 201
    return r.json()["data"]["invoice_id"]


def delete(client, iid, who=KTT, password=PW):
    return client.request("DELETE", f"/api/invoices/{iid}", json={"password": password}, headers=login(client, who))


def test_ktt_cannot_do_accountant_work(client):
    iid = upload_xml(client)
    h = login(client, KTT)
    assert client.post("/api/invoices", files={"file": ("a.xml", b"<HDon/>")}, headers=h).status_code == 403
    assert client.post(f"/api/invoices/{iid}/reprocess", headers=h).status_code == 403
    fid = client.get(f"/api/invoices/{iid}/fields", headers=h).json()["data"][0]["field_id"]
    assert client.patch(f"/api/invoices/{iid}/fields/{fid}", json={"final_value": "X"}, headers=h).status_code == 403
    for method, url in [("post", f"/api/invoices/{iid}/suggest-entries"), ("put", f"/api/invoices/{iid}/journal-entries"),
                        ("post", f"/api/invoices/{iid}/submit"), ("post", f"/api/invoices/{iid}/match-po"),
                        ("post", "/api/purchase-orders")]:
        assert getattr(client, method)(url, headers=h).status_code == 403, url


def test_ktv_cannot_do_chief_work(client):
    iid = upload_xml(client)
    h = login(client, KTV)
    assert client.post(f"/api/invoices/{iid}/approve", headers=h).status_code == 403
    assert client.post(f"/api/invoices/{iid}/reject", headers=h).status_code == 403
    assert client.get("/api/approvals", headers=h).status_code == 403
    assert delete(client, iid, who=KTV).status_code == 403
    assert client.get(f"/api/invoices/{iid}", headers=h).status_code == 200   # van xem duoc


def test_fields_editable_only_for_ktv(client):
    iid = upload_xml(client)
    assert client.get(f"/api/invoices/{iid}/fields", headers=login(client, KTV)).json()["editable"] is True
    assert client.get(f"/api/invoices/{iid}/fields", headers=login(client, KTT)).json()["editable"] is False


def test_ktt_can_view_everything_read_only(client):
    iid = upload_xml(client)
    h = login(client, KTT)
    assert client.get("/api/invoices", headers=h).status_code == 200
    assert client.get(f"/api/invoices/{iid}", headers=h).status_code == 200
    assert client.get(f"/api/invoices/{iid}/file", headers=h).status_code == 200
    assert client.get("/api/approvals", headers=h).status_code == 200


def test_delete_needs_password_and_removes_everything(client):
    iid = upload_xml(client)
    with SessionLocal() as db:
        path = settings.upload_dir / db.get(Invoice, iid).file_path
        assert db.query(InvoiceField).filter_by(invoice_id=iid).count() > 0
    assert path.is_file()
    assert delete(client, iid, password="sai-mat-khau").status_code == 403
    assert client.request("DELETE", f"/api/invoices/{iid}", headers=login(client, KTT)).status_code == 422   # khong gui body
    assert delete(client, iid, password="").status_code == 400                                                # mat khau rong
    assert client.get(f"/api/invoices/{iid}", headers=login(client, KTT)).status_code == 200                  # chua mat
    assert delete(client, iid).status_code == 200
    assert client.get(f"/api/invoices/{iid}", headers=login(client, KTT)).status_code == 404
    with SessionLocal() as db:
        assert db.query(InvoiceField).filter_by(invoice_id=iid).count() == 0
    assert not path.exists()
    assert delete(client, iid).status_code == 404


def test_delete_blocked_when_processing_or_exported(client):
    iid = upload_xml(client)
    with SessionLocal() as db:
        db.get(Invoice, iid).status = "dang_xu_ly"
        db.commit()
    assert delete(client, iid).status_code == 409
    with SessionLocal() as db:
        inv = db.get(Invoice, iid)
        inv.status, inv.export_status = "da_duyet", "da_xuat"
        db.commit()
    assert delete(client, iid).status_code == 409
