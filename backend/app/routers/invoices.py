"""Goi A (A4, A8): tai hoa don, danh sach, chi tiet, mo file goc, kiem tra so bo. Day la endpoint THAT.

Dinh dang tra ve giu nhu hop dong mock: {"data": ...} (danh sach co them "total").
"""
import uuid
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db
from app.models import Invoice, User
from app.security import get_current_user
from app.services import ai_client
from app.services.checks import run_checks
from app.services.invoice_data import display_name, process_invoice
from app.services.xml_parser import XmlInvoiceError, parse_invoice_xml

router = APIRouter(prefix="/api/invoices", tags=["A"])

MAX_BYTES = 10 * 1024 * 1024
# phan mo rong -> (file_type, kiem tra "chu ky" dau file)
ALLOWED = {
    ".pdf": ("pdf", lambda h: h.startswith(b"%PDF")),
    ".png": ("image", lambda h: h.startswith(b"\x89PNG\r\n\x1a\n")),
    ".jpg": ("image", lambda h: h.startswith(b"\xff\xd8\xff")),
    ".jpeg": ("image", lambda h: h.startswith(b"\xff\xd8\xff")),
    ".xml": ("xml", lambda h: h.lstrip(b"\xef\xbb\xbf \t\r\n").startswith(b"<")),
}
MEDIA = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg",
         ".jpeg": "image/jpeg", ".xml": "application/xml"}
REPROCESSABLE = {"loi_xu_ly", "dang_xu_ly", "cho_xac_nhan"}


def _num(v: Decimal | None) -> str | None:
    return None if v is None else format(v, "f")


def invoice_out(i: Invoice) -> dict:
    return {
        "invoice_id": i.invoice_id, "filename": display_name(i.file_path), "file_type": i.file_type,
        "uploaded_by": i.uploaded_by,
        "invoice_series": i.invoice_series, "invoice_number": i.invoice_number,
        "invoice_date": i.invoice_date.isoformat() if i.invoice_date else None,
        "seller_name": i.seller_name, "mst_seller": i.mst_seller,
        "total_before_tax": _num(i.total_before_tax), "vat_rate": _num(i.vat_rate),
        "vat_amount": _num(i.vat_amount), "total_amount": _num(i.total_amount),
        "deduct_group": i.deduct_group, "status": i.status, "reject_reason": i.reject_reason,
        "export_status": i.export_status,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


def _get_or_404(db: Session, invoice_id: int) -> Invoice:
    inv = db.get(Invoice, invoice_id)
    if inv is None:
        raise HTTPException(404, "Không tìm thấy hóa đơn")
    return inv


def _process_in_background(invoice_id: int) -> None:
    with SessionLocal() as db:
        process_invoice(db, invoice_id)


@router.post("", status_code=201)
def upload_invoice(background: BackgroundTasks, file: UploadFile = File(...),
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(415, "Chỉ nhận PDF, PNG, JPG hoặc XML")
    file_type, magic_ok = ALLOWED[ext]
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File lớn hơn 10 MB")
    if not data or not magic_ok(data[:16]):
        raise HTTPException(415, "Nội dung file không khớp với phần đuôi tên file")
    if file_type == "xml":  # XML sai thi tu choi luon, khong luu
        try:
            parse_invoice_xml(data)
        except XmlInvoiceError as e:
            raise HTTPException(422, str(e))

    safe = "".join(c if c.isalnum() or c in "-." else "-" for c in Path(file.filename).stem)[:60] or "hoa-don"
    stored = f"{uuid.uuid4().hex[:12]}_{safe}{ext}"
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    (settings.upload_dir / stored).write_bytes(data)

    inv = Invoice(uploaded_by=user.user_id, file_path=stored, file_type=file_type, status="dang_xu_ly")
    db.add(inv)
    db.commit()
    if file_type == "xml":
        process_invoice(db, inv.invoice_id)  # nhanh, khong can AI nen xu ly ngay
        db.refresh(inv)
    else:
        background.add_task(_process_in_background, inv.invoice_id)
    return {"data": invoice_out(inv)}


@router.get("/{invoice_id}/progress")
def invoice_progress(invoice_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Tien do doc du lieu de giao dien ve thanh tien do. Het 'dang_xu_ly' thi percent = 100."""
    inv = _get_or_404(db, invoice_id)
    if inv.status != "dang_xu_ly":
        return {"data": {"status": inv.status, "percent": 100,
                         "stage": "Không đọc được hóa đơn" if inv.status == "loi_xu_ly" else "Hoàn tất"}}
    p = ai_client.get_progress(inv.file_path) or {"percent": 5, "stage": "Đang chờ xử lý"}
    return {"data": {"status": inv.status, **p}}


@router.get("")
def list_invoices(status: str | None = None, file_type: str | None = None, q: str | None = None,
                  date_from: str | None = None, date_to: str | None = None,
                  limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                  db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    from app.services.normalize import parse_date
    cond = []
    if status:
        cond.append(Invoice.status == status)
    if file_type:
        cond.append(Invoice.file_type == file_type)
    if q:
        like = f"%{q.strip()}%"
        cond.append(or_(Invoice.invoice_number.like(like), Invoice.seller_name.like(like),
                        Invoice.mst_seller.like(like), Invoice.file_path.like(like)))
    for raw, op in ((date_from, "ge"), (date_to, "le")):
        if raw:
            d = parse_date(raw)
            if d is None:
                raise HTTPException(422, f"Ngày không hợp lệ: {raw}")
            cond.append(Invoice.invoice_date >= d if op == "ge" else Invoice.invoice_date <= d)
    total = db.scalar(select(func.count()).select_from(Invoice).where(*cond))
    rows = db.scalars(select(Invoice).where(*cond).order_by(Invoice.invoice_id.desc())
                      .limit(limit).offset(offset))
    return {"data": [invoice_out(r) for r in rows], "total": total}


@router.get("/{invoice_id}")
def get_invoice(invoice_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    inv = _get_or_404(db, invoice_id)
    return {"data": {**invoice_out(inv), "checks": run_checks(db, inv)}}


@router.get("/{invoice_id}/file")
def get_invoice_file(invoice_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Chung tu tai chinh: bat buoc dang nhap (Bearer token)."""
    inv = _get_or_404(db, invoice_id)
    base = settings.upload_dir.resolve()
    path = (base / inv.file_path).resolve()
    if base not in path.parents or not path.is_file():  # chan ../ va file mat
        raise HTTPException(404, "Không tìm thấy file gốc")
    return FileResponse(path, media_type=MEDIA.get(path.suffix.lower(), "application/octet-stream"),
                        filename=display_name(inv.file_path), content_disposition_type="inline",
                        headers={"X-Content-Type-Options": "nosniff"})


@router.post("/{invoice_id}/check")
def check_invoice(invoice_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    inv = _get_or_404(db, invoice_id)
    result = run_checks(db, inv)
    result["vendor_suggestion"] = None
    if inv.seller_name:
        known = list(db.scalars(select(Invoice.seller_name).where(
            Invoice.seller_name.is_not(None), Invoice.invoice_id != inv.invoice_id).distinct()))
        if inv.mst_seller:  # cung MST thi uu tien ten da co
            same = list(db.scalars(select(Invoice.seller_name).where(
                Invoice.mst_seller == inv.mst_seller, Invoice.seller_name.is_not(None),
                Invoice.invoice_id != inv.invoice_id).distinct()))
            known = same or known
        norm = ai_client.normalize_vendor(inv.seller_name, known) if known else None
        if norm and norm.get("matched") and norm["canonical"] != inv.seller_name:
            result["vendor_suggestion"] = norm
            result["issues"].append(f"Ten nguoi ban giong '{norm['canonical']}' ({norm['score']:.0f}%) - nen thong nhat")
    return {"data": result}


@router.post("/{invoice_id}/reprocess")
def reprocess(invoice_id: int, background: BackgroundTasks, db: Session = Depends(get_db),
              _: User = Depends(get_current_user)):
    """Chay lai trich xuat khi loi_xu_ly (VD ai-service tat hoac het han muc Gemini)."""
    inv = _get_or_404(db, invoice_id)
    if inv.status not in REPROCESSABLE:
        raise HTTPException(409, f"Hóa đơn đang ở trạng thái {inv.status}, không thể xử lý lại")
    inv.status = "dang_xu_ly"
    db.commit()
    if inv.file_type == "xml":
        process_invoice(db, inv.invoice_id)
        db.refresh(inv)
    else:
        background.add_task(_process_in_background, inv.invoice_id)
    return {"data": invoice_out(inv)}
