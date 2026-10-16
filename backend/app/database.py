"""Ket noi CSDL bang SQLAlchemy co connection pool (tranh loi 'Too many connections')."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

_url = settings.database_url
_kwargs = {"pool_pre_ping": True}
if not _url.startswith("sqlite"):
    # pool_recycle < wait_timeout cua MySQL de khong bi cat ket noi nhan roi
    _kwargs.update(pool_size=5, max_overflow=10, pool_recycle=1800)

engine = create_engine(_url, **_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
