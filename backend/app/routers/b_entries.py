"""Goi B (B6): goi y va luu but toan Nợ/Có cho hoa don. Day la endpoint THAT.

Mot dong but toan = mot ben No + mot ben Co + so tien. Hoa don co thue sinh 2 dong (khoan muc chinh va thue GTGT 1331).
"""
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account, Invoice, JournalEntry, User
from app.routers.b_fields import EDITABLE_STATUSES
from app.security import get_current_user, require_role
from app.services import gl_suggest

router = APIRouter(prefix="/api/invoices", tags=["B"])
MAX_LINES = 20
MAX_AMOUNT = Decimal("9999999999999999.99")  # Numeric(18, 2)


def _invoice(db: Session, invoice_id: int) -> Invoice:
    inv = db.get(Invoice, invoice_id)
    if inv is None:
        raise HTTPException(404, "Không tìm thấy hóa đơn")
    return inv


def entry_out(e: JournalEntry) -> dict:
    return {"journal_entry_id": e.journal_entry_id, "debit_account": e.debit_account,
            "credit_account": e.credit_account, "amount": format(e.amount, "f")}


@router.get("/{invoice_id}/journal-entries")
def get_entries(invoice_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inv = _invoice(db, invoice_id)
    rows = db.scalars(select(JournalEntry).where(JournalEntry.invoice_id == invoice_id)
                      .order_by(JournalEntry.journal_entry_id))
    # chi ke toan vien sua but toan; ke toan truong chi xem
    return {"data": [entry_out(e) for e in rows], "editable": inv.status in EDITABLE_STATUSES and user.role_name == "KTV"}


@router.post("/{invoice_id}/suggest-entries")
def suggest_entries(invoice_id: int, db: Session = Depends(get_db), _: User = Depends(require_role("KTV"))):
    inv = _invoice(db, invoice_id)
    if inv.status in ("dang_xu_ly", "loi_xu_ly"):
        raise HTTPException(409, "Hóa đơn chưa đọc xong nên chưa gợi ý được định khoản")
    try:
        result = gl_suggest.suggest(db, inv)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"data": result["entries"], "warnings": result["warnings"]}


class EntryIn(BaseModel):
    debit_account: str = Field(min_length=1, max_length=10)
    credit_account: str = Field(min_length=1, max_length=10)
    amount: Decimal

    @field_validator("debit_account", "credit_account")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @field_validator("amount", mode="before")
    @classmethod
    def _amount(cls, v):
        try:
            d = Decimal(str(v).strip())
        except (InvalidOperation, ValueError):
            raise ValueError("Số tiền không hợp lệ")
        if not d.is_finite() or d <= 0 or d > MAX_AMOUNT:
            raise ValueError("Số tiền phải lớn hơn 0")
        if d != d.quantize(Decimal("0.01")):
            raise ValueError("Số tiền chỉ được có tối đa 2 chữ số thập phân")
        return d


class EntriesIn(BaseModel):
    entries: list[EntryIn] = Field(min_length=1, max_length=MAX_LINES)


@router.put("/{invoice_id}/journal-entries")
def put_entries(invoice_id: int, body: EntriesIn, db: Session = Depends(get_db), _: User = Depends(require_role("KTV"))):
    """Thay toan bo but toan cua hoa don bang danh sach gui len (khong cong don)."""
    inv = _invoice(db, invoice_id)
    if inv.status not in EDITABLE_STATUSES:
        raise HTTPException(409, f"Hóa đơn đang ở trạng thái “{inv.status}”, không thể sửa bút toán")
    codes = {c for e in body.entries for c in (e.debit_account, e.credit_account)}
    known = set(db.scalars(select(Account.account_code).where(Account.account_code.in_(codes))))
    if codes - known:
        raise HTTPException(422, "Tài khoản không có trong danh mục: " + ", ".join(sorted(codes - known)))
    for i, e in enumerate(body.entries, 1):
        if e.debit_account == e.credit_account:
            raise HTTPException(422, f"Dòng {i}: tài khoản Nợ và Có không được trùng nhau")

    db.execute(delete(JournalEntry).where(JournalEntry.invoice_id == invoice_id))
    rows = [JournalEntry(invoice_id=invoice_id, debit_account=e.debit_account, credit_account=e.credit_account,
                         amount=e.amount) for e in body.entries]
    db.add_all(rows)
    db.commit()
    warnings = []
    total = sum((e.amount for e in body.entries), Decimal(0))
    if inv.total_amount is not None and abs(total - inv.total_amount) > Decimal(1):
        warnings.append("Tổng tiền các dòng khác tổng thanh toán trên hóa đơn")
    return {"data": [entry_out(r) for r in rows], "warnings": warnings}
