"""Kiem tra ket noi CSDL (chi doc, khong ghi). Chay: python scripts/check_db.py
Doc cac bien DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_SSL giong luc chay that."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import engine  # noqa: E402

print(f"Dang ket noi {settings.db_host}:{settings.db_port} / {settings.db_name} "
      f"(user={settings.db_user}, SSL={os.getenv('DB_SSL', '0')}) ...")
try:
    with engine.connect() as c:
        print("OK  phien ban:", c.execute(text("SELECT VERSION()")).scalar())
        try:
            print("OK  TLS    :", c.execute(text("SHOW STATUS LIKE 'Ssl_cipher'")).fetchone())
        except Exception:
            pass
        tables = [r[0] for r in c.execute(text("SHOW TABLES"))]
        print("OK  so bang:", len(tables), tables)
        print("OK  da migrate:", "alembic_version" in tables)
except Exception as e:  # noqa: BLE001
    print("LOI:", type(e).__name__, e)
    sys.exit(1)
