"""Luu file hoa don trong CSDL (bang invoice_file_chunks). Dia cuc bo (settings.upload_dir) chi la bo nho dem:
nen tang free (Render) xoa dia moi lan khoi dong lai, nen khi can file ma dia khong con thi dung lai tu CSDL."""
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import settings
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
