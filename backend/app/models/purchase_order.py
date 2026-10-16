"""Bang purchase_orders (Goi C): don dat hang de doi chieu voi hoa don."""
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    po_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    po_number: Mapped[str] = mapped_column(String(30), unique=True)
    vendor: Mapped[str] = mapped_column(String(200))
    order_date: Mapped[date] = mapped_column(Date)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    # Nhom tu dinh nghia gia tri, vi du: dang_mo | da_doi_chieu
    status: Mapped[str] = mapped_column(String(20), default="dang_mo")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
