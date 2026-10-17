#!/usr/bin/env python3
"""A10: do do chinh xac trich xuat (PaddleOCR + Gemini/quy tac) tren bo hoa don gia data_test/.

Can ai-service dang chay (mac dinh http://localhost:8001). Chay tu thu muc goc bang Python nao cung duoc
(script tu dung Python cua ai-service/venv). Moi hoa don duoc gui qua POST /extract, ket qua
duoc so voi labels.json. Xuat vao eval_out/<ten-lan-chay>/:
    raw/<id>.json    phan hoi day du cua ai-service (gom do tin cay tung truong)
    pred/<id>.json   dinh dang cho tools/score_fields.py
    report.md        bang do chinh xac tung truong (anh sach / anh nhieu) + bang hieu chuan do tin cay

Vi du:
  python tools/eval_extraction.py --source images --run paddle_llm          # PaddleOCR + Gemini (can GEMINI_API_KEY)
  python tools/eval_extraction.py --source images --no-llm --run paddle_rules   # PaddleOCR + regex
  python tools/eval_extraction.py --source images --no-preprocess --run paddle_llm_nopre   # bo tien xu ly anh
  python tools/eval_extraction.py --source pdf_ocr --run pdf_forced_ocr    # ep PDF di qua OCR
  python tools/eval_extraction.py --source pdf --no-llm --run pdf_text     # PDF co lop chu (khong OCR)

LUU Y KHI GHI BAO CAO: bo du lieu la hoa don GIA (12 hoa don, mau trinh bay don gian), nen so lieu chi la
mau nho, khong the suy ra do chinh xac tren hoa don that.
"""
import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _venv import ensure_venv  # noqa: E402

ensure_venv(needs=("httpx",))   # tu dung Python cua ai-service/venv neu Python hien tai thieu httpx

import httpx  # noqa: E402
from score_fields import norm  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data_test"
# ten truong cua he thong -> ten truong trong labels.json / score_fields.py
FIELD_MAP = {
    "invoice_series": "ky_hieu", "invoice_number": "so_hoa_don", "invoice_date": "ngay_lap",
    "seller_name": "ten_nguoi_ban", "mst_seller": "mst_nguoi_ban", "total_before_tax": "tong_truoc_thue",
    "vat_rate": "thue_suat", "vat_amount": "tien_thue", "total_amount": "tong_thanh_toan",
}


def _fold(s: str) -> str:
    import unicodedata
    s = str(s).replace("đ", "d").replace("Đ", "D")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return "".join(s.casefold().split())


def same(field: str, got, want) -> bool:
    if got in (None, ""):
        return False
    lab = FIELD_MAP[field]
    if field == "seller_name":
        return _fold(got) == _fold(want)
    if field == "invoice_date":  # ai-service tra ISO, nhan la dd/mm/yyyy
        y, m, d = str(got).split("-")
        return f"{d}/{m}/{y}" == want
    if field == "total_before_tax":
        return norm("tong_thanh_toan", got) == norm("tong_thanh_toan", want)
    return norm(lab, got) == norm(lab, want)


def band(conf: float) -> str:
    return "xanh >=90" if conf >= 90 else "vang 70-90" if conf >= 70 else "do <70"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://localhost:8001")
    ap.add_argument("--source", choices=["images", "pdf", "pdf_ocr"], default="images",
                    help="images: PNG qua PaddleOCR; pdf: doc lop chu; pdf_ocr: ep PDF qua PaddleOCR")
    ap.add_argument("--no-llm", action="store_true", help="chi dung quy tac regex")
    ap.add_argument("--no-preprocess", action="store_true", help="tat tien xu ly anh (de so sanh)")
    ap.add_argument("--run", default=None, help="ten thu muc ket qua trong eval_out/")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--pause", type=float, default=0, help="nghi giua cac lan goi (giay) de khoi vuot han muc Gemini")
    a = ap.parse_args()

    run = a.run or f"{a.source}{'_rules' if a.no_llm else '_llm'}{'_nopre' if a.no_preprocess else ''}"
    out = ROOT / "eval_out" / run
    (out / "raw").mkdir(parents=True, exist_ok=True)
    (out / "pred").mkdir(parents=True, exist_ok=True)
    labels = json.loads((DATA / "labels.json").read_text(encoding="utf-8"))
    if a.limit:
        labels = labels[: a.limit]

    ok, tot = defaultdict(int), defaultdict(int)
    ok_g, tot_g = defaultdict(int), defaultdict(int)       # (truong, sach|nhieu)
    cal_ok, cal_tot = defaultdict(int), defaultdict(int)   # (band) -> dung/tong
    sources = defaultdict(int)
    times, fails, warns = [], [], 0
    for lab in labels:
        sub, ext = ("images", "png") if a.source == "images" else ("pdf", "pdf")
        path = DATA / sub / f"{lab['id']}.{ext}"
        form = {"use_llm": str(not a.no_llm).lower(), "preprocess": str(not a.no_preprocess).lower(),
                "force_ocr": str(a.source == "pdf_ocr").lower()}
        t0 = time.time()
        try:
            r = httpx.post(f"{a.url}/extract", data=form, files={"file": (path.name, path.read_bytes())}, timeout=300)
            r.raise_for_status()
            data = r.json()["data"]
        except (httpx.HTTPError, KeyError, ValueError) as e:
            fails.append((lab["id"], str(e)[:120]))
            continue
        times.append(time.time() - t0)
        (out / "raw" / f"{lab['id']}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        sources[data["source"]] += 1
        warns += bool(data["warnings"])
        grp = "nhieu" if lab.get("lam_nhieu") else "sach"
        pred = {}
        for f, k in FIELD_MAP.items():
            item = data["fields"][f]
            got = item["value"]
            hit = same(f, got, lab[k])
            tot[f] += 1; tot_g[(f, grp)] += 1
            ok[f] += hit; ok_g[(f, grp)] += hit
            b = band(item["confidence"])
            cal_tot[b] += 1; cal_ok[b] += hit
            if got is not None and k in ("ky_hieu", "so_hoa_don", "mst_nguoi_ban", "tong_thanh_toan", "thue_suat", "tien_thue"):
                pred[k] = got
            if f == "invoice_date" and got:
                y, m, d = got.split("-"); pred[k] = f"{d}/{m}/{y}"
        (out / "pred" / f"{lab['id']}.json").write_text(json.dumps(pred, ensure_ascii=False), encoding="utf-8")
        if a.pause:
            time.sleep(a.pause)

    n = len(times)
    pct = lambda x, y: f"{x / y:.0%}" if y else "-"  # noqa: E731
    lines = [f"# Ket qua danh gia `{run}`", "",
             f"- Nguon: **{a.source}**, LLM: **{'tat' if a.no_llm else 'bat'}**, tien xu ly anh: **{'tat' if a.no_preprocess else 'bat'}**",
             f"- Hoa don doc duoc: **{n}/{len(labels)}**; nguon trich xuat: {dict(sources)}; co canh bao: {warns}",
             f"- Thoi gian trung binh moi hoa don: **{sum(times) / n:.1f} s**" if n else "- Khong hoa don nao doc duoc",
             "- Du lieu GIA, mau nho: khong suy ra duoc do chinh xac tren hoa don that.", "",
             "## Do chinh xac tung truong", "",
             "| Truong | Dung/Tong | Ti le | Anh sach | Anh nhieu |", "|---|---:|---:|---:|---:|"]
    for f in FIELD_MAP:
        lines.append(f"| {f} | {ok[f]}/{tot[f]} | {pct(ok[f], tot[f])} | {pct(ok_g[(f, 'sach')], tot_g[(f, 'sach')])} | "
                     f"{pct(ok_g[(f, 'nhieu')], tot_g[(f, 'nhieu')])} |")
    all_ok, all_tot = sum(ok.values()), sum(tot.values())
    lines += [f"| **Tong** | {all_ok}/{all_tot} | {pct(all_ok, all_tot)} | | |", "",
              "## Hieu chuan do tin cay (cac o co do tin cay cao co dung that khong?)", "",
              "| Dai | So o | Dung | Ti le dung |", "|---|---:|---:|---:|"]
    for b in ("xanh >=90", "vang 70-90", "do <70"):
        lines.append(f"| {b} | {cal_tot[b]} | {cal_ok[b]} | {pct(cal_ok[b], cal_tot[b])} |")
    if fails:
        lines += ["", "## Loi", ""] + [f"- {i}: {m}" for i, m in fails]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nDa ghi {out}")


if __name__ == "__main__":
    main()
