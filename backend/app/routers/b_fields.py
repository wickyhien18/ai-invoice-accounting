"""Goi B (B2): doc va sua cac truong AI/XML da trich xuat. Day la endpoint THAT.

- extracted_value luon giu nguyen gia tri may doc; ke toan sua thi ghi vao final_value.
- final_value = gia tri may doc (gui lai y het) nghia la "da xac nhan dung"; gui null de bo sua.
- Mau do tin cay: xanh >= 90, vang 70..<90, do < 70 (khong co diem = do vi chua duoc kiem chung).
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Invoice, InvoiceField, User
from app.routers.invoices import invoice_out
from app.security import get_current_user, require_role
from app.services.checks import run_checks
from app.services.invoice_data import sync_invoice_from_fields
from app.services.normalize import FIELD_NAMES, canonical

router = APIRouter(prefix="/api/invoices", tags=["B"])

EDITABLE_STATUSES = ("cho_xac_nhan", "tu_choi")  # da gui duyet / da duyet thi khoa, tranh sua duoi chan nguoi duyet
MAX_LEN = {"invoice_series": 10, "invoice_number": 20, "mst_seller": 14, "seller_name": 200}  # theo cot bang invoices
HINT = {"invoice_date": "ngày hợp lệ, ví dụ 23/06/2026", "vat_rate": "số, ví dụ 8 hoặc 10",
        "total_before_tax": "số tiền, ví dụ 3.882.100", "vat_amount": "số tiền, ví dụ 310.568",
        "total_amount": "số tiền, ví dụ 4.192.668", "mst_seller": "chữ số (và dấu -), ví dụ 0487211601"}


def confidence_level(score: Decimal | None) -> str:
    if score is None or score < 70:
        return "red"
    return "green" if score >= 90 else "yellow"


def field_out(f: InvoiceField) -> dict:
    return {
        "field_id": f.field_id, "field_name": f.field_name,
        "extracted_value": f.extracted_value, "final_value": f.final_value,
        "value": f.final_value if f.final_value is not None else f.extracted_value,
        "confirmed": f.final_value is not None,
        "edited": f.final_value is not None and f.final_value != f.extracted_value,
        "confidence_score": None if f.confidence_score is None else float(f.confidence_score),
        "confidence_level": confidence_level(f.confidence_score),
    }


def _invoice(db: Session, invoice_id: int) -> Invoice:
    inv = db.get(Invoice, invoice_id)
    if inv is None:
        raise HTTPException(404, "Không tìm thấy hóa đơn")
    return inv


def _fields(db: Session, invoice_id: int) -> list[InvoiceField]:
    rows = list(db.scalars(select(InvoiceField).where(InvoiceField.invoice_id == invoice_id)))
    order = {n: i for i, n in enumerate(FIELD_NAMES)}
    return sorted(rows, key=lambda r: (order.get(r.field_name, 99), r.field_id))


@router.get("/{invoice_id}/fields")
def get_fields(invoice_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inv = _invoice(db, invoice_id)
    return {"data": [field_out(f) for f in _fields(db, invoice_id)],
            "status": inv.status, "file_type": inv.file_type,
            # chi ke toan vien sua truong; ke toan truong chi xem
            "editable": inv.status in EDITABLE_STATUSES and user.role_name == "KTV"}


class FieldPatch(BaseModel):
    final_value: str | None = Field(None, max_length=255)


@router.patch("/{invoice_id}/fields/{field_id}")
def patch_field(invoice_id: int, field_id: int, body: FieldPatch, db: Session = Depends(get_db),
                _: User = Depends(require_role("KTV"))):
    inv = _invoice(db, invoice_id)
    field = db.get(InvoiceField, field_id)
    if field is None or field.invoice_id != invoice_id:
        raise HTTPException(404, "Không tìm thấy trường")
    if inv.status not in EDITABLE_STATUSES:
        raise HTTPException(409, f"Hóa đơn đang ở trạng thái “{inv.status}”, không thể sửa trường")

    raw = (body.final_value or "").strip()
    if not raw:
        field.final_value = None   # bo sua: quay ve gia tri may doc
    else:
        value = canonical(field.field_name, raw)
        if not value:
            raise HTTPException(422, f"Giá trị không hợp lệ, cần {HINT.get(field.field_name, 'một giá trị khác rỗng')}")
        if len(value) > MAX_LEN.get(field.field_name, 255):
            raise HTTPException(422, f"Giá trị quá dài (tối đa {MAX_LEN[field.field_name]} ký tự)")
        field.final_value = value
    db.flush()
    sync_invoice_from_fields(db, inv)  # bang invoices luon khop voi truong da sua
    db.commit()
    db.refresh(inv)
    return {"data": field_out(field), "invoice": invoice_out(inv), "checks": run_checks(db, inv)}
