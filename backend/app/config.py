"""Doc cau hinh tu file .env DUY NHAT o thu muc goc cua du an."""
import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


class Settings:
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "3306")
    db_user = os.getenv("DB_USER", "app_user")
    db_password = os.getenv("DB_PASSWORD", "app_password")
    db_name = os.getenv("DB_NAME", "ai_invoice_db")
    secret_key = os.getenv("SECRET_KEY", "change_me_to_a_long_random_string")
    access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    ai_service_url = os.getenv("AI_SERVICE_URL", "http://localhost:8001")
    upload_dir = Path(os.getenv("UPLOAD_DIR", "storage/uploads"))

    @property
    def database_url(self) -> str:
        # DATABASE_URL chi dung cho test (VD sqlite); chay that dung cac bien DB_*
        override = os.getenv("DATABASE_URL")
        if override:
            return override
        return (
            f"mysql+pymysql://{quote_plus(self.db_user)}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


settings = Settings()
