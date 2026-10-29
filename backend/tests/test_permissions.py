"""Dang ky tai khoan va quy tac 'hoa don cua ai nguoi do sua'."""
import pytest

from app.config import settings
from tests.conftest import login

XML = (b'<?xml version="1.0" encoding="UTF-8"?><HDon><DLHDon><TTChung><KHHDon>C26TAA</KHHDon><SHDon>1</SHDon>'
       b'<NLap>2026-01-15</NLap></TTChung><NDHDon><NBan><Ten>CTY A</Ten><MST>0100000000</MST></NBan>'
       b'<TToan><TgTCThue>1000</TgTCThue><TgTThue>100</TgTThue><TgTTTBSo>1100</TgTTTBSo></TToan></NDHDon></DLHDon></HDon>')


def reg(client, **over):
    body = {"full_name": "Nguyễn Văn B", "email": "ktv2@t.local", "password": "matkhau123", **over}
    return client.post("/api/auth/register", json=body)


def bearer(r):
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def invite(monkeypatch):
    monkeypatch.setattr(settings, "ktt_invite_code", "MA-MOI-123")


def test_register_creates_ktv_and_logs_in(client):
    r = reg(client)
    assert r.status_code == 201
    assert r.json()["user"]["role_name"] == "KTV"
    assert client.get("/api/auth/me", headers=bearer(r)).json()["email"] == "ktv2@t.local"
    # dang nhap lai duoc, khong phan biet hoa thuong email
    assert client.post("/api/auth/login", json={"email": " KTV2@T.local ", "password": "matkhau123"}).status_code == 200


def test_register_rejects_bad_input(client):
    assert reg(client, password="ngan").status_code == 422
    assert reg(client, email="khong-phai-email").status_code == 422
    assert reg(client, full_name="A").status_code == 422
    assert reg(client, role_name="ADMIN").status_code == 422
    assert reg(client, password="ư" * 40).status_code == 422  # 80 byte > gioi han 72 cua bcrypt


def test_register_duplicate_email(client):
    assert reg(client).status_code == 201
    assert reg(client, email="KTV2@t.local").status_code == 409      # khac hoa thuong van la trung
    assert reg(client, email="ktv@t.local").status_code == 409       # trung tai khoan co san


def test_register_ktt_needs_invite_code(client, invite):
    assert reg(client, email="a@t.local", role_name="KTT").status_code == 403
    assert reg(client, email="a@t.local", role_name="KTT", invite_code="sai").status_code == 403
    r = reg(client, email="a@t.local", role_name="KTT", invite_code="MA-MOI-123")
    assert r.status_code == 201 and r.json()["user"]["role_name"] == "KTT"


def test_register_ktt_disabled_when_no_code(client, monkeypatch):
    monkeypatch.setattr(settings, "ktt_invite_code", "")
    assert reg(client, role_name="KTT", invite_code="").status_code == 403


def upload(client, headers):
    r = client.post("/api/invoices", headers=headers, files={"file": ("hd.xml", XML, "application/xml")})
    assert r.status_code == 201, r.text
    return r.json()["data"]


def test_owner_can_edit_others_cannot(client):
    a = login(client, "ktv@t.local")
    b = bearer(reg(client))
    inv = upload(client, a)
    assert inv["can_edit"] is True and inv["uploaded_by_name"] == "KTV"
    i = inv["invoice_id"]

    # KTV khac: xem duoc nhung KHONG sua duoc
    seen = client.get(f"/api/invoices/{i}", headers=b).json()["data"]
    assert seen["can_edit"] is False and seen["uploaded_by_name"] == "KTV"
    r = client.post(f"/api/invoices/{i}/reprocess", headers=b)
    assert r.status_code == 403 and "KTV" in r.json()["detail"]
    for method, path in [("patch", f"/api/invoices/{i}/fields/1"), ("post", f"/api/invoices/{i}/suggest-entries"),
                         ("put", f"/api/invoices/{i}/journal-entries"), ("post", f"/api/invoices/{i}/submit")]:
        assert getattr(client, method)(path, headers=b).status_code == 403, path
        assert getattr(client, method)(path, headers=a).status_code == 200, path  # chu hoa don thi duoc


def test_ktt_cannot_touch_ktv_work_but_can_approve(client):
    a, t = login(client, "ktv@t.local"), login(client, "ktt@t.local")
    i = upload(client, a)["invoice_id"]
    assert client.post("/api/invoices", headers=t, files={"file": ("hd.xml", XML, "application/xml")}).status_code == 403
    assert client.post(f"/api/invoices/{i}/reprocess", headers=t).status_code == 403
    assert client.patch(f"/api/invoices/{i}/fields/1", headers=t).status_code == 403
    assert client.post(f"/api/invoices/{i}/submit", headers=t).status_code == 403
    assert client.get(f"/api/invoices/{i}", headers=t).json()["data"]["can_edit"] is False  # van xem duoc
    assert client.post(f"/api/invoices/{i}/approve", headers=t).status_code == 200


def test_edit_endpoint_404_for_missing_invoice(client):
    assert client.post("/api/invoices/999/reprocess", headers=login(client, "ktv@t.local")).status_code == 404


def test_list_mine_filter_and_owner_names(client):
    a = login(client, "ktv@t.local")
    b = bearer(reg(client))
    upload(client, a)
    upload(client, b)
    allr = client.get("/api/invoices", headers=a).json()
    assert allr["total"] == 2 and {r["uploaded_by_name"] for r in allr["data"]} == {"KTV", "Nguyễn Văn B"}
    mine = client.get("/api/invoices?mine=true", headers=a).json()
    assert mine["total"] == 1 and mine["data"][0]["can_edit"] is True
    assert all(r["can_edit"] for r in mine["data"])


def test_test_mode_ktt_can_work_like_ktv_but_ktv_still_cannot_approve(client, monkeypatch):
    monkeypatch.setattr(settings, "ktt_can_work", True)
    a, t = login(client, "ktv@t.local"), login(client, "ktt@t.local")
    assert client.get("/api/auth/me", headers=t).json()["can_work"] is True
    inv = upload(client, t)                                            # KTT tai duoc o che do test
    assert inv["can_edit"] is True
    i = inv["invoice_id"]
    assert client.post(f"/api/invoices/{i}/reprocess", headers=t).status_code == 200   # va sua duoc hoa don cua minh
    assert client.patch(f"/api/invoices/{i}/fields/1", headers=t).status_code == 200
    assert client.patch(f"/api/invoices/{i}/fields/1", headers=a).status_code == 403   # KTV khac van khong sua duoc
    own = upload(client, a)["invoice_id"]
    assert client.post(f"/api/invoices/{own}/reprocess", headers=t).status_code == 403  # KTT khong sua hoa don cua KTV
    assert client.post(f"/api/invoices/{i}/approve", headers=a).status_code == 403     # KTV khong duyet duoc
    assert client.post(f"/api/invoices/{i}/approve", headers=t).status_code == 200     # KTT van duyet


def test_default_mode_can_work_flag(client):
    assert client.get("/api/auth/me", headers=login(client, "ktv@t.local")).json()["can_work"] is True
    assert client.get("/api/auth/me", headers=login(client, "ktt@t.local")).json()["can_work"] is False
