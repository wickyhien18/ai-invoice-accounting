"""Bang invoice_fields (Goi A): tung truong AI doc. So sanh extracted_value va final_value de biet truong nao da bi sua."""
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InvoiceField(Base):
    __tablename__ = "invoice_fields"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    field_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.invoice_id"))
    field_name: Mapped[str] = mapped_column(String(50))
    extracted_value: Mapped[str | None] = mapped_column(String(255))
    final_value: Mapped[str | None] = mapped_column(String(255))
    # Do tin cay (%): xanh >= 90, vang 70..<90, do < 70
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("item_categories.category_id"))
