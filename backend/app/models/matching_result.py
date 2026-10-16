"""Bang matching_results (Goi C). Hoa don khong co PO thi khong co dong nao o day."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MatchingResult(Base):
    __tablename__ = "matching_results"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.invoice_id"))
    po_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.po_id"))
    amount_difference: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    match_status: Mapped[str] = mapped_column(String(20))  # khop | lech
    checked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
