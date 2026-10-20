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


def test_only_ktt_can_approve(client):
    assert client.post("/api/invoices/1/approve", headers=login(client, "ktv@t.local")).status_code == 403
    assert client.post("/api/invoices/1/approve", headers=login(client, "ktt@t.local")).status_code == 200


def test_mock_contract_needs_login_and_flags_mock(client):
    assert client.get("/api/purchase-orders").status_code == 401
    r = client.get("/api/purchase-orders", headers=login(client, "ktv@t.local")).json()
    assert r["mock"] is True
