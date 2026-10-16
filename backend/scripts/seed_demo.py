"""CHI DUNG KHI PHAT TRIEN: tao 2 tai khoan demo + nap he thong tai khoan. Chay trong backend/:
    python scripts/seed_demo.py
Mat khau demo chi de dev, TUYET DOI khong dung khi trien khai that."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402
from scripts.seed_coa import main as seed_coa  # noqa: E402

DEMO = [
    ("Ke toan vien Demo", "ktv@demo.local", "ktv12345", "KTV"),
    ("Ke toan truong Demo", "ktt@demo.local", "ktt12345", "KTT"),
]


def main() -> None:
    seed_coa()
    with SessionLocal() as db:
        for name, email, pw, role in DEMO:
            if db.scalar(select(User).where(User.email == email)) is None:
                db.add(User(full_name=name, email=email, password_hash=hash_password(pw), role_name=role))
        db.commit()
    print("Tai khoan demo: ktv@demo.local / ktv12345 (KTV), ktt@demo.local / ktt12345 (KTT)")


if __name__ == "__main__":
    main()
