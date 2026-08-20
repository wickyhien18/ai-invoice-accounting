"""
MySQL connection configuration for the backend.

This service does NOT have its own .env file — it loads the single
.env file located at the project root (one level above backend/,
ai-service/, frontend/). This keeps all environment variables (MySQL
credentials, JWT secret, AI service URL, LLM API key, etc.) in one
place instead of scattered across multiple .env files.

Key points to keep when extending this file:
- pool_pre_ping=True: SQLAlchemy checks the connection is still alive
  before using it, avoiding "MySQL server has gone away" errors when
  the connection has been idle for a long time (common when the
  backend is left running overnight without a restart).
- pool_recycle=3600: connections are closed and recreated every hour,
  avoiding issues where MySQL silently drops old connections
  (MySQL's own wait_timeout) that SQLAlchemy is unaware of.
- charset=utf8mb4: ensures correct read/write of non-ASCII text
  (e.g. names or descriptions containing accented characters).
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Root .env is two levels up from this file: backend/app/database.py -> project root
ROOT_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=ROOT_ENV_PATH)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "app_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "app_password")
DB_NAME = os.getenv("DB_NAME", "ai_invoice_db")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?charset=utf8mb4"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
    echo=False,  # set to True temporarily when debugging SQL queries
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: db: Session = Depends(get_db)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
