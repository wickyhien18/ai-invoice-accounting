"""Kiem tra hang loat: ke toan vien kiem tra tung hoa don -> LUU (da_luu), cuoi cung GUI CA LO cho ke toan truong.

- POST /api/invoices/{id}/save-review : (can co but toan) chot ket qua kiem tra, hoa don thanh 'da_luu' (van sua lai duoc).
- POST /api/invoices/submit-batch     : tat ca hoa don 'da_luu' (hoac danh sach id gui kem) -> 'cho_duyet'.
Chi ke toan vien (KTV) duoc dung.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Invoice, JournalEntry, User
from app.security import require_role

router = APIRouter(prefix="/api/invoices", tags=["B"])
REVIEWABLE = ("cho_xac_nhan", "tu_choi", "da_luu")


@router.post("/{invoice_id}/save-review")
def save_review(invoice_id: int, db: Session = Depends(get_db), _: User = Depends(require_role("KTV"))):
    inv = db.get(Invoice, invoice_id)
    if inv is None:
        raise HTTPException(404, "Không tìm thấy hóa đơn")
    if inv.status not in REVIEWABLE:
        raise HTTPException(409, f"Hóa đơn đang ở trạng thái “{inv.status}”, không thể lưu kiểm tra")
    if not db.scalar(select(func.count()).select_from(JournalEntry).where(JournalEntry.invoice_id == invoice_id)):
        raise HTTPException(409, "Hóa đơn chưa có bút toán. Hãy gán định khoản trước khi lưu kiểm tra")
    inv.status = "da_luu"   # giu nguyen reject_reason: hoa don tu choi sau khi luu van thuoc "lo tu choi"
    db.commit()
    return {"data": {"invoice_id": inv.invoice_id, "status": inv.status}}


class BatchIn(BaseModel):
    invoice_ids: list[int] | None = Field(default=None, max_length=500)


@router.post("/submit-batch")
def submit_batch(body: BatchIn | None = None, db: Session = Depends(get_db), _: User = Depends(require_role("KTV"))):
    q = select(Invoice).where(Invoice.status == "da_luu")
    if body and body.invoice_ids is not None:
        q = q.where(Invoice.invoice_id.in_(body.invoice_ids))
    rows = list(db.scalars(q))
    for r in rows:
        r.status = "cho_duyet"
    db.commit()
    return {"data": {"sent": len(rows), "invoice_ids": [r.invoice_id for r in rows]}}
