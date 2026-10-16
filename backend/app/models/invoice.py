"""Bang invoices (Goi A): hoa don. Trang thai duyet (status) va xuat (export_status) tach rieng.

status: dang_xu_ly | cho_xac_nhan | cho_duyet | da_duyet | tu_choi
export_status: chua_xuat | da_xuat
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    invoice_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    file_path: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(10))  # xml | pdf | image
    invoice_series: Mapped[str | None] = mapped_column(String(10))
    invoice_number: Mapped[str | None] = mapped_column(String(20))
    invoice_date: Mapped[date | None] = mapped_column(Date)
    seller_name: Mapped[str | None] = mapped_column(String(200))
    mst_seller: Mapped[str | None] = mapped_column(String(14))
    total_before_tax: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    vat_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    vat_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    deduct_group: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="dang_xu_ly")
    reject_reason: Mapped[str | None] = mapped_column(String(255))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    export_status: Mapped[str] = mapped_column(String(20), default="chua_xuat")
    exported_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
