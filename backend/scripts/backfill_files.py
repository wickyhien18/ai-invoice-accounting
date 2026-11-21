"""Khoi phuc file goc cho hoa don demo da nap TRUOC khi co bang invoice_file_chunks (chi hoa don co
file_path bat dau bang 'demo' va co file tuong ung trong data_test). An toan khi chay lai nhieu lan."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select  # noqa: E402

from app.config import ROOT_DIR  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import Invoice  # noqa: E402
from app.services.file_store import has_file, save_file  # noqa: E402
from app.services.invoice_data import display_name  # noqa: E402

DATA = ROOT_DIR / "data_test"


def main() -> int:
    n = 0
    with SessionLocal() as db:
        for inv in db.scalars(select(Invoice).where(Invoice.file_path.like("demo%"))):
            if has_file(db, inv.invoice_id):
                continue
            name = display_name(inv.file_path)
            src = next((p for sub in ("images", "pdf", "xml") if (p := DATA / sub / name).is_file()), None)
            if src is None:
                continue
            save_file(db, inv.invoice_id, src.read_bytes())
            n += 1
        db.commit()
    return n


if __name__ == "__main__":
    print(f"Da khoi phuc file goc cho {main()} hoa don demo.")
