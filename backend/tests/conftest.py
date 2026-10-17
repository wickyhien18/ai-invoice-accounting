import os
import sys
from pathlib import Path

# DB tam bang SQLite de test khong can MySQL. Phai dat TRUOC khi import app.
os.environ["DATABASE_URL"] = "sqlite:///./test_tmp.db"
os.environ["UPLOAD_DIR"] = "test_uploads_tmp"  # thu muc tam cua test
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402


@pytest.fixture(autouse=True)
def db_setup():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add_all([
            User(full_name="KTV", email="ktv@t.local", password_hash=hash_password("pw123456"), role_name="KTV"),
            User(full_name="KTT", email="ktt@t.local", password_hash=hash_password("pw123456"), role_name="KTT"),
        ])
        db.commit()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def login(client, email):
    r = client.post("/api/auth/login", json={"email": email, "password": "pw123456"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
