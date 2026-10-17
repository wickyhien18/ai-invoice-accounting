"""A3: nap hoa don demo tu data_test/labels.json vao CSDL (kem invoice_fields) de Khanh va Duong
lam viec ma khong cho OCR. Chay trong backend/ (can da co 2 tai khoan demo):
    python scripts/seed_invoices.py
Chay lai nhieu lan van an toan (bo qua hoa don da co cung ky hieu + so + MST).

Quy tac demo (co dinh, khong ngau nhien giua cac lan chay):
- anh lam nhieu (lam_nhieu=true) -> file_type image, do tin cay 55..95; anh sach -> pdf (moi hoa don
  thu 3 la xml), do tin cay 92..99. Nho vay man hinh mau xanh/vang/do cua Khanh co du ca ba mau.
- trang thai xoay vong: 6 cho_xac_nhan, 3 cho_duyet, 2 da_duyet, 1 tu_choi (cho luong duyet cua Duong).
"""
import json
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select  # noqa: E402

from app.config import ROOT_DIR, settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import Invoice, User  # noqa: E402
from app.services.invoice_data import save_extraction  # noqa: E402

DATA = ROOT_DIR / "data_test"
STATUS_CYCLE = ["cho_xac_nhan"] * 6 + ["cho_duyet"] * 3 + ["da_duyet"] * 2 + ["tu_choi"]


def build_fields(lab: dict, rng: random.Random) -> dict:
    values = {
        "invoice_series": lab["ky_hieu"], "invoice_number": lab["so_hoa_don"],
        "invoice_date": lab["ngay_lap"], "seller_name": lab["ten_nguoi_ban"],
        "mst_seller": lab["mst_nguoi_ban"], "total_before_tax": lab["tong_truoc_thue"],
        "vat_rate": lab["thue_suat"], "vat_amount": lab["tien_thue"], "total_amount": lab["tong_thanh_toan"],
    }
    lo, hi = (55, 95) if lab.get("lam_nhieu") else (92, 99)
    return {k: {"value": v, "confidence": round(rng.uniform(lo, hi), 2)} for k, v in values.items()}


def seed_invoices() -> int:
    labels = json.loads((DATA / "labels.json").read_text(encoding="utf-8"))
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    added = 0
    with SessionLocal() as db:
        uploader = db.scalar(select(User).where(User.email == "ktv@demo.local"))
        approver = db.scalar(select(User).where(User.email == "ktt@demo.local"))
        if uploader is None:
            raise SystemExit("Chua co tai khoan demo. Chay python scripts/seed_demo.py")
        for idx, lab in enumerate(labels):
            exists = db.scalar(select(Invoice.invoice_id).where(
                Invoice.invoice_series == lab["ky_hieu"], Invoice.invoice_number == lab["so_hoa_don"],
                Invoice.mst_seller == lab["mst_nguoi_ban"]))
            if exists:
                continue
            if lab.get("lam_nhieu"):
                kind, src = "image", DATA / "images" / f"{lab['id']}.png"
            elif idx % 3 == 0 and (DATA / "xml" / f"{lab['id']}.xml").exists():
                kind, src = "xml", DATA / "xml" / f"{lab['id']}.xml"
            else:
                kind, src = "pdf", DATA / "pdf" / f"{lab['id']}.pdf"
            stored = f"demo{lab['id'].lower()}_{src.name}"
            shutil.copyfile(src, settings.upload_dir / stored)
            status = STATUS_CYCLE[idx % len(STATUS_CYCLE)]
            inv = Invoice(uploaded_by=uploader.user_id, file_path=stored, file_type=kind, status=status)
            if status == "tu_choi":
                inv.reject_reason = "Demo: sai so tien, de nghi kiem tra lai"
            if status in ("da_duyet", "tu_choi") and approver:
                inv.approved_by = approver.user_id
            db.add(inv)
            db.flush()
            fields = build_fields(lab, random.Random(lab["id"]))
            if kind == "xml":
                for f in fields.values():
                    f["confidence"] = 100
            save_extraction(db, inv, fields)
            added += 1
        db.commit()
    return added


def main() -> None:
    print(f"Da them {seed_invoices()} hoa don demo.")


if __name__ == "__main__":
    main()
