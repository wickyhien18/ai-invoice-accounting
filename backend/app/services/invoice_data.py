"""Luu ket qua trich xuat vao invoice_fields va dong bo sang cot cua invoices.

Goi B (sua truong) nen goi sync_invoice_from_fields() sau khi ghi final_value de bang invoices luon khop.
"""
import logging
import threading
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Invoice, InvoiceField
from app.services import ai_client
from app.services.normalize import FIELD_NAMES, canonical, to_column
from app.services.xml_parser import XmlInvoiceError, parse_invoice_xml

log = logging.getLogger(__name__)


def save_extraction(db: Session, inv: Invoice, fields: dict) -> None:
    """Thay toan bo invoice_fields cua hoa don bang ket qua moi va cap nhat cot invoices."""
    db.execute(delete(InvoiceField).where(InvoiceField.invoice_id == inv.invoice_id))
    for name in FIELD_NAMES:
        item = fields.get(name) or {}
        value = canonical(name, item.get("value"))
        conf = item.get("confidence")
        db.add(InvoiceField(
            invoice_id=inv.invoice_id, field_name=name, extracted_value=value,
            confidence_score=None if conf is None else Decimal(str(round(float(conf), 2))),
        ))
    db.flush()
    sync_invoice_from_fields(db, inv)


def sync_invoice_from_fields(db: Session, inv: Invoice) -> None:
    """Cot invoices = final_value neu ke toan da sua, nguoc lai extracted_value."""
    rows = db.scalars(select(InvoiceField).where(InvoiceField.invoice_id == inv.invoice_id))
    for row in rows:
        if row.field_name not in FIELD_NAMES:
            continue
        value = row.final_value if row.final_value is not None else row.extracted_value
        col = {"invoice_series": "invoice_series", "invoice_number": "invoice_number",
               "invoice_date": "invoice_date", "seller_name": "seller_name", "mst_seller": "mst_seller",
               "total_before_tax": "total_before_tax", "vat_rate": "vat_rate",
               "vat_amount": "vat_amount", "total_amount": "total_amount"}[row.field_name]
        setattr(inv, col, to_column(row.field_name, value))


def extract_fields(inv: Invoice) -> dict:
    """XML doc truc tiep; PDF/anh goi ai-service. Nem XmlInvoiceError / AIServiceError."""
    path = settings.upload_dir / inv.file_path
    if inv.file_type == "xml":
        return parse_invoice_xml(path.read_bytes())
    return ai_client.extract_invoice(path, display_name(inv.file_path))


def display_name(file_path: str) -> str:
    """file_path luu dang '<ma>_<ten goc>'; tra lai ten goc de hien thi."""
    return file_path.split("_", 1)[1] if "_" in file_path else file_path


def process_invoice(db: Session, invoice_id: int) -> str:
    """Chay trich xuat, dat trang thai cho_xac_nhan (xong) hoac loi_xu_ly (loi). Tra ve trang thai."""
    inv = db.get(Invoice, invoice_id)
    if inv is None:
        return "khong_ton_tai"
    try:
        result = extract_fields(inv)
        save_extraction(db, inv, result["fields"])
        inv.status = "cho_xac_nhan"
    except Exception as e:  # MOI loi deu phai ra loi_xu_ly; neu de lot thi hoa don ket 'dang_xu_ly' mai mai
        known = isinstance(e, (XmlInvoiceError, ai_client.AIServiceError, OSError, KeyError))
        log.error("Xu ly hoa don %s loi: %s", invoice_id, e, exc_info=not known)
        db.rollback()
        inv = db.get(Invoice, invoice_id)
        inv.status = "loi_xu_ly"
    db.commit()
    return inv.status


# ---- Xu ly nen: PDF/anh doc LAN LUOT de moi hoa don deu xong, khong tranh nhau/qua han ----
_SCAN_LOCK = threading.Lock()


def run_in_background(invoice_id: int) -> None:
    """Chay process_invoice trong luong nen. Cac hoa don xep hang o day (khong giu ket noi toi ai-service
    luc cho), ai-service chi nhan MOT yeu cau moi lan -> khong timeout khi tai nhieu file."""
    with _SCAN_LOCK:
        with SessionLocal() as db:
            process_invoice(db, invoice_id)


def recover_stuck() -> int:
    """Luc khoi dong lai backend, nhung hoa don con 'dang_xu_ly' (tac vu nen bi mat do tat/reload) duoc xu ly lai
    lan luot. Tra ve so hoa don duoc nhat lai."""
    with SessionLocal() as db:
        ids = list(db.scalars(select(Invoice.invoice_id).where(Invoice.status == "dang_xu_ly")
                              .order_by(Invoice.invoice_id)))
    for i in ids:
        run_in_background(i)
    return len(ids)


def recover_stuck_in_thread() -> None:
    def work():
        try:
            n = recover_stuck()
            if n:
                log.info("Da xu ly lai %s hoa don bi do dang luc khoi dong", n)
        except Exception:
            log.exception("Khong nhat lai duoc hoa don dang do")
    threading.Thread(target=work, daemon=True, name="recover-invoices").start()
