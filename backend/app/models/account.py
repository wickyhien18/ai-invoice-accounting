"""Bang chart_of_accounts (Goi B): danh muc tai khoan theo TT133."""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Account(Base):
    __tablename__ = "chart_of_accounts"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    account_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    account_name: Mapped[str] = mapped_column(String(200))
