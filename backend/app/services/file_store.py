"""Luu file hoa don trong CSDL (bang invoice_file_chunks). Dia cuc bo (settings.upload_dir) chi la bo nho dem:
nen tang free (Render) xoa dia moi lan khoi dong lai, nen khi can file ma dia khong con thi dung lai tu CSDL."""
from pathlib import Path

from sqlalchemy import delete, exists, func, select
from sqlalchemy.orm import Session

from app.config import ROOT_DIR, settings
from app.models import Invoice, InvoiceFileChunk

CHUNK_SIZE = 1024 * 1024  # 1 MiB moi dong, du nho de khong cham gioi han dong cua TiDB


def save_file(db: Session, invoice_id: int, data: bytes) -> int:
    """Ghi file thanh cac manh (khong commit; nguoi goi commit cung luc voi hoa don). Tra ve so manh."""
    db.execute(delete(InvoiceFileChunk).where(InvoiceFileChunk.invoice_id == invoice_id))
    n = 0
    for seq, start in enumerate(range(0, len(data), CHUNK_SIZE)):
        db.add(InvoiceFileChunk(invoice_id=invoice_id, seq=seq, content=data[start:start + CHUNK_SIZE]))
        n += 1
    return n


def has_file(db: Session, invoice_id: int) -> bool:
    return db.scalar(select(func.count()).select_from(InvoiceFileChunk)
                     .where(InvoiceFileChunk.invoice_id == invoice_id)) > 0


def read_file(db: Session, invoice_id: int) -> bytes | None:
    rows = db.scalars(select(InvoiceFileChunk.content).where(InvoiceFileChunk.invoice_id == invoice_id)
                      .order_by(InvoiceFileChunk.seq)).all()
    return b"".join(rows) if rows else None


def local_path(inv: Invoice) -> Path | None:
    """Duong dan trong thu muc upload; None neu ten file co ../ (chan thoat khoi thu muc)."""
    base = settings.upload_dir.resolve()
    path = (base / inv.file_path).resolve()
    return path if base in path.parents else None


def ensure_local(db: Session, inv: Invoice) -> Path | None:
    """Tra ve duong dan file tren dia, dung lai tu CSDL neu dia da bi xoa. None neu khong co o dau ca."""
    path = local_path(inv)
    if path is None:
        return None
    if path.is_file():
        return path
    data = read_file(db, inv.invoice_id)
    if data is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


MAX_BYTES = 10 * 1024 * 1024


def backfill_missing(db: Session) -> int:
    """Hoa don chua co ban trong CSDL (nap truoc khi co bang invoice_file_chunks): lay tu dia cuc bo, hoac voi
    hoa don demo thi lay tu data_test. Chay lai nhieu lan van an toan. Tra ve so hoa don da bo sung."""
    pending = db.scalars(select(Invoice).where(
        ~exists().where(InvoiceFileChunk.invoice_id == Invoice.invoice_id))).all()
    n = 0
    for inv in pending:
        path = local_path(inv)
        if path is None or not path.is_file():
            path = None
            if inv.file_path.startswith("demo") and "_" in inv.file_path:
                name = inv.file_path.split("_", 1)[1]
                path = next((p for sub in ("images", "pdf", "xml") if (p := ROOT_DIR / "data_test" / sub / name).is_file()), None)
        if path is None or path.stat().st_size > MAX_BYTES:
            continue
        save_file(db, inv.invoice_id, path.read_bytes())
        n += 1
    db.commit()
    return n
