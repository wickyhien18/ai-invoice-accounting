from tests.conftest import login


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_login_ok_and_bad(client):
    assert client.post("/api/auth/login", json={"email": "ktv@t.local", "password": "pw123456"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "ktv@t.local", "password": "sai"}).status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
    me = client.get("/api/auth/me", headers=login(client, "ktv@t.local")).json()
    assert me["role_name"] == "KTV"


def _invoice(status):
    from app.database import SessionLocal
    from app.models import Invoice
    with SessionLocal() as db:
        inv = Invoice(uploaded_by=1, file_path="x.xml", file_type="xml", status=status)
        db.add(inv)
        db.commit()
        return inv.invoice_id


def test_only_ktt_can_approve(client):
    iid = _invoice("cho_duyet")
    assert client.post(f"/api/invoices/{iid}/approve", headers=login(client, "ktv@t.local")).status_code == 403
    assert client.post("/api/invoices/999/approve", headers=login(client, "ktt@t.local")).status_code == 404
    assert client.post(f"/api/invoices/{iid}/approve", headers=login(client, "ktt@t.local")).status_code == 200


def test_approve_reject_only_pending_invoices(client):
    h = login(client, "ktt@t.local")
    for st in ("dang_xu_ly", "cho_xac_nhan", "da_duyet", "tu_choi"):
        iid = _invoice(st)
        r = client.post(f"/api/invoices/{iid}/approve", headers=h)
        assert r.status_code == 409 and "dang_xu_ly" not in r.json()["detail"], st
        assert client.post(f"/api/invoices/{iid}/reject?reason=x", headers=h).status_code == 409, st
    iid = _invoice("cho_duyet")
    assert client.post(f"/api/invoices/{iid}/reject?reason=%20%20", headers=h).status_code == 400
    assert client.post(f"/api/invoices/{iid}/reject?reason=Sai%20MST", headers=h).status_code == 200


def test_purchase_orders_need_login(client):
    assert client.get("/api/purchase-orders").status_code == 401
