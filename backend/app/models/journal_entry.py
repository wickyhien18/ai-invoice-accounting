"""Bang journal_entries (Goi B): mot dong co mot ben No va mot ben Co. Hoa don co thue sinh 2 dong."""
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JournalEntry(Base):
    __tablename__ = "journal_entries"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    journal_entry_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.invoice_id"))
    debit_account: Mapped[str] = mapped_column(String(10), ForeignKey("chart_of_accounts.account_code"))
    credit_account: Mapped[str] = mapped_column(String(10), ForeignKey("chart_of_accounts.account_code"))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
