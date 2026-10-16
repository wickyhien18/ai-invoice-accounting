"""Nap he thong tai khoan TT133 tu database/seed/chart_of_accounts_tt133.csv. Chay trong backend/:
    python scripts/seed_coa.py
Chay lai nhieu lan van an toan (bo qua tai khoan da co)."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import ROOT_DIR  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import Account  # noqa: E402

CSV_PATH = ROOT_DIR / "database" / "seed" / "chart_of_accounts_tt133.csv"


def main() -> None:
    with SessionLocal() as db, open(CSV_PATH, encoding="utf-8", newline="") as f:
        added = 0
        for row in csv.DictReader(f):
            if db.get(Account, row["account_code"]) is None:
                db.add(Account(account_code=row["account_code"], account_name=row["account_name"]))
                added += 1
        db.commit()
    print(f"Da them {added} tai khoan.")


if __name__ == "__main__":
    main()
