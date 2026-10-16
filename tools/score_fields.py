#!/usr/bin/env python3
"""Cham diem ket qua trich xuat so voi nhan chuan.

Dau vao:
  --labels  labels.json do gen_invoices.py tao
  --pred    thu muc chua <id>.json cho moi hoa don, vi du HD001.json:
            {"so_hoa_don": "3837994", "ky_hieu": "C26TBB", "ngay_lap": "02/01/2026",
             "mst_nguoi_ban": "0915000806", "tong_thanh_toan": 77758600}
Chi cham cac truong co trong file du doan. Tien duoc so sanh sau khi bo dau cham/phay.

Chay:  python score_fields.py --labels data_test/labels.json --pred pred/
"""
import argparse, json, re
from collections import defaultdict
from pathlib import Path

FIELDS = ["so_hoa_don", "ky_hieu", "ngay_lap", "mst_nguoi_ban", "tong_thanh_toan", "thue_suat", "tien_thue"]
MONEY = {"tong_thanh_toan", "tien_thue", "tong_truoc_thue"}


def norm(field, v):
    s = str(v).strip().lower()
    if field in MONEY:
        return re.sub(r"[^\d]", "", s)
    if field in ("so_hoa_don", "mst_nguoi_ban", "thue_suat"):
        return re.sub(r"[^\d]", "", s).lstrip("0") or "0"
    s = re.sub(r"\s+", "", s)
    if field == "ky_hieu" and len(s) == 7 and s[0].isdigit():  # chap nhan "1C26TAA" cho "C26TAA"
        s = s[1:]
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--pred", required=True)
    a = ap.parse_args()
    labels = {l["id"]: l for l in json.load(open(a.labels, encoding="utf-8"))}
    ok, tot = defaultdict(int), defaultdict(int)
    ok_n, tot_n = defaultdict(int), defaultdict(int)  # tach anh sach / anh nhieu
    missing = 0
    for id_, lab in labels.items():
        p = Path(a.pred) / f"{id_}.json"
        if not p.exists():
            missing += 1
            continue
        pred = json.load(open(p, encoding="utf-8"))
        grp = "nhieu" if lab.get("lam_nhieu") else "sach"
        for f in FIELDS:
            if f not in pred:
                continue
            tot[f] += 1
            tot_n[(f, grp)] += 1
            if norm(f, pred[f]) == norm(f, lab[f]):
                ok[f] += 1
                ok_n[(f, grp)] += 1
    print(f"Thieu file du doan: {missing}/{len(labels)}")
    print(f"{'truong':<18}{'dung/tong':>12}{'ti le':>9}{'sach':>10}{'nhieu':>10}")
    for f in FIELDS:
        if not tot[f]:
            continue
        def r(g):
            t = tot_n[(f, g)]
            return f"{ok_n[(f, g)] / t:.0%}" if t else "-"
        print(f"{f:<18}{ok[f]:>6}/{tot[f]:<5}{ok[f] / tot[f]:>9.0%}{r('sach'):>10}{r('nhieu'):>10}")


if __name__ == "__main__":
    main()
