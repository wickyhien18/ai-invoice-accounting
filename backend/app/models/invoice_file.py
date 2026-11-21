"""Bang invoice_file_chunks: noi dung file hoa don luu trong CSDL, cat thanh manh <= 1 MB (moi manh 1 dong)
de khong vuot gioi han kich thuoc 1 dong cua TiDB (mac dinh 6 MiB). Dia cuc bo chi con la bo nho dem."""
from sqlalchemy import ForeignKey, Integer, LargeBinary
from sqlalchemy.dialects.mysql import MEDIUMBLOB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InvoiceFileChunk(Base):
    __tablename__ = "invoice_file_chunks"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.invoice_id"), primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    content: Mapped[bytes] = mapped_column(LargeBinary().with_variant(MEDIUMBLOB(), "mysql"))
