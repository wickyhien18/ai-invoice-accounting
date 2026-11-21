"""Tu nang cap CSDL (alembic upgrade head) luc backend khoi dong, de chay local giong ban deploy:
khong con loi 'bang chua ton tai' khi keo ma moi co migration moi ve. Chi ap dung cho MySQL/TiDB; bo qua SQLite
(dung cho test). Tat bang AUTO_MIGRATE=0. Loi thi chi ghi log, khong lam backend khong khoi dong duoc."""
import logging
import os
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import settings

log = logging.getLogger("uvicorn.error")
BACKEND_DIR = Path(__file__).resolve().parents[1]


def upgrade_and_backfill() -> None:
    if os.getenv("AUTO_MIGRATE", "1") == "0" or not settings.database_url.startswith("mysql"):
        return
    try:
        cfg = Config(str(BACKEND_DIR / "alembic.ini"))
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        command.upgrade(cfg, "head")
        from app.database import SessionLocal
        from app.services.file_store import backfill_missing
        with SessionLocal() as db:
            n = backfill_missing(db)
        if n:
            log.info("Da bo sung file goc vao CSDL cho %s hoa don", n)
    except Exception as e:  # noqa: BLE001
        log.error("Tu nang cap CSDL that bai (chay tay: alembic upgrade head): %s", e)
