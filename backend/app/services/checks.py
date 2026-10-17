"""A8: kiem tra so bo hoa don (khong dung AI): MST, tong tien, hoa don trung."""
import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Invoice

MST_RE = re.compile(r"^(\d{10}|\d{10}-\d{3}|\d{13})$")
TOLERANCE = Decimal("1")  # lech toi da 1 dong do lam tron


def check_mst(mst: str | None) -> bool:
    """MST hop le: 10 chu so, 13 chu so, hoac 10 so-3 so. Chi kiem dinh dang, khong tra cuu co quan thue."""
    return bool(mst and MST_RE.match(mst))


def check_totals(before: Decimal | None, rate: Decimal | None, vat: Decimal | None,
                 total: Decimal | None) -> tuple[bool | None, list[str]]:
    """Tra ve (khop?, danh sach loi). None neu thieu so lieu de kiem tra."""
    issues: list[str] = []
    if before is None or vat is None or total is None:
        return None, ["Thieu tien truoc thue, tien thue hoac tong thanh toan nen khong kiem tra duoc tong tien"]
    if abs(before + vat - total) > TOLERANCE:
        issues.append(f"Tien truoc thue {before} + thue {vat} = {before + vat}, khac tong thanh toan {total}")
    if rate is not None:
        expected = before * rate / Decimal(100)
        if abs(expected - vat) > TOLERANCE:
            issues.append(f"Thue suat {rate}% tren {before} phai la {expected.quantize(Decimal('1'))}, hoa don ghi {vat}")
    return (not issues), issues


def find_duplicates(db: Session, inv: Invoice) -> list[int]:
    """Hoa don khac co cung ky hieu + so hoa don + MST nguoi ban."""
    if not (inv.invoice_series and inv.invoice_number and inv.mst_seller):
        return []
    q = select(Invoice.invoice_id).where(
        Invoice.invoice_series == inv.invoice_series,
        Invoice.invoice_number == inv.invoice_number,
        Invoice.mst_seller == inv.mst_seller,
        Invoice.invoice_id != inv.invoice_id,
    )
    return list(db.scalars(q))


def run_checks(db: Session, inv: Invoice) -> dict:
    issues: list[str] = []
    mst_ok = check_mst(inv.mst_seller)
    if not mst_ok:
        issues.append("MST nguoi ban thieu hoac sai dinh dang" if not inv.mst_seller
                      else f"MST nguoi ban '{inv.mst_seller}' sai dinh dang (can 10 hoac 13 chu so)")
    total_ok, total_issues = check_totals(inv.total_before_tax, inv.vat_rate, inv.vat_amount, inv.total_amount)
    issues += total_issues
    dups = find_duplicates(db, inv)
    if dups:
        issues.append(f"Trung ky hieu, so hoa don va MST voi hoa don {dups}")
    return {"mst_valid": mst_ok, "total_matches": total_ok, "duplicate": bool(dups),
            "duplicate_of": dups, "issues": issues}
