"""B7: nap vai loai khoan mau kem cach viet khac (alias) cho man hinh dinh khoan. Chay trong backend/:
    python scripts/seed_categories.py
Chay lai nhieu lan van an toan. Chi chon alias KHONG phu thuoc so tien (vi alias duoc uu tien hon mo hinh ML);
loai phu thuoc so tien (VD thiet bi IT: 153 hay 211) de mo hinh quyet dinh. Ke toan truong co the sua o trang Danh muc."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import Account, CategoryAlias, ItemCategory  # noqa: E402

CATEGORIES = [
    ("Vận chuyển, quảng cáo", "6421", ["vận tải", "vận chuyển", "giao nhận", "quảng cáo"]),
    ("Điện, nước, viễn thông", "6422", ["điện lực", "cấp nước", "viễn thông", "internet"]),
    ("Dịch vụ tư vấn, kiểm toán", "6422", ["tư vấn", "kiểm toán", "pháp lý"]),
    ("Nguyên vật liệu", "152", ["nguyên liệu", "vật liệu", "vật tư"]),
    ("Chi phí tài chính", "635", ["tài chính", "ngân hàng"]),
]


def main() -> None:
    added = 0
    with SessionLocal() as db:
        codes = set(db.scalars(select(Account.account_code)))
        for name, debit, aliases in CATEGORIES:
            cat = db.scalar(select(ItemCategory).where(ItemCategory.category_name == name))
            if cat is None:
                cat = ItemCategory(category_name=name, default_debit_account=debit if debit in codes else None)
                db.add(cat)
                db.flush()
                added += 1
            have = {a.lower() for a in db.scalars(select(CategoryAlias.alias_text))}
            for a in aliases:
                if a.lower() not in have:
                    db.add(CategoryAlias(alias_text=a, category_id=cat.category_id))
        db.commit()
    print(f"Da them {added} loai khoan (chay seed_coa truoc de co tai khoan No mac dinh).")


if __name__ == "__main__":
    main()
