"""Bang item_categories va category_aliases (Goi B): khoan muc chuan va cac cach viet khac nhau."""
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ItemCategory(Base):
    __tablename__ = "item_categories"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    category_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_name: Mapped[str] = mapped_column(String(100), unique=True)
    default_debit_account: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("chart_of_accounts.account_code"), nullable=True)


class CategoryAlias(Base):
    __tablename__ = "category_aliases"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    alias_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    alias_text: Mapped[str] = mapped_column(String(150))
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("item_categories.category_id"))
