"""Nap du lieu demo (he thong tai khoan, 2 tai khoan demo, 12 hoa don) CHI KHI chua co nguoi dung nao.
Dung cho lan deploy dau (SEED_DEMO=1); khoi dong lai se khong nap lap."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import func, select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402

with SessionLocal() as db:
    n = db.scalar(select(func.count()).select_from(User))
if n:
    print(f"Da co {n} nguoi dung, bo qua nap du lieu demo.")
else:
    from scripts.seed_demo import main
    main()
