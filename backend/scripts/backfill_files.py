"""Bo sung ban luu trong CSDL cho hoa don chua co (nap truoc khi co bang invoice_file_chunks): lay file tu dia
cuc bo, hoac data_test voi hoa don demo. An toan khi chay lai nhieu lan. Chay trong backend/:
    python scripts/backfill_files.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal  # noqa: E402
from app.services.file_store import backfill_missing  # noqa: E402

if __name__ == "__main__":
    with SessionLocal() as db:
        print(f"Da bo sung file goc vao CSDL cho {backfill_missing(db)} hoa don.")
