"""
Cấu hình kết nối MySQL cho backend.

Điểm quan trọng cần giữ nguyên khi mở rộng:
- pool_pre_ping=True: SQLAlchemy tự kiểm tra kết nối còn sống trước khi dùng,
  tránh lỗi "MySQL server has gone away" khi kết nối bị timeout do không dùng
  trong thời gian dài (rất hay gặp khi để backend chạy qua đêm rồi hôm sau
  test lại mà không restart).
- pool_recycle=3600: tự đóng và tạo lại kết nối sau 1 giờ, tránh việc MySQL
  tự ngắt kết nối cũ (mặc định MySQL có wait_timeout) mà SQLAlchemy không biết.
- charset=utf8mb4: đảm bảo đọc/ghi đúng tiếng Việt có dấu.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

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
    echo=False,  # đổi thành True khi cần debug SQL query
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency dùng trong FastAPI route: db: Session = Depends(get_db)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
