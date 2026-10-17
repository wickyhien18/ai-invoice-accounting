#!/usr/bin/env python3
"""Soi tung buoc doc MOT anh/PDF: OCR doc ra gi, quy tac regex lay duoc gi, Gemini co duoc dung khong.

Dung khi anh doc sai/thieu truong de biet LOI O DAU (OCR, quy tac, hay Gemini). Khong can chay server.
Chay tu thu muc goc du an bang Python nao cung duoc: script tu dung Python cua ai-service/venv
(tao venv mot lan theo SETUP.md muc 3.1, khong can kich hoat):

    python tools/debug_ocr.py data_test/images/HD001.png
    python tools/debug_ocr.py data_test/images/HD001.png --no-preprocess     # thu khong tien xu ly anh
    python tools/debug_ocr.py data_test/images/HD001.png --no-llm            # chi OCR + quy tac
    python tools/debug_ocr.py data_test/images/HD001.png --save-prep out.png # luu anh sau tien xu ly de xem

Gui toan bo phan in ra (hoac chup man hinh) neu can nho nguoi khac xem giup.
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai-service"))
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

from _venv import ensure_venv  # noqa: E402

ensure_venv(needs=("dotenv", "rapidfuzz", "PIL", "numpy", "pymupdf"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from app.services import extractor, ocr  # noqa: E402
from app.services.rules import rule_extract  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--no-preprocess", action="store_true")
    ap.add_argument("--force-ocr", action="store_true", help="ep PDF di qua OCR")
    ap.add_argument("--save-prep", metavar="PNG", help="luu anh sau tien xu ly")
    a = ap.parse_args()

    path = Path(a.file)
    data = path.read_bytes()
    print(f"== Moi truong: GEMINI_API_KEY {'CO' if os.getenv('GEMINI_API_KEY') else 'KHONG CO'}, "
          f"LLM_MODEL={os.getenv('LLM_MODEL', '(mac dinh)')}, LLM_MASK={os.getenv('LLM_MASK', '1')}")

    if a.save_prep and path.suffix.lower() in (".png", ".jpg", ".jpeg"):
        from PIL import Image

        from app.services.preprocess import preprocess
        preprocess(Image.open(path)).save(a.save_prep)
        print(f"== Da luu anh sau tien xu ly: {a.save_prep}")

    print("\n== 1. OCR (dong | do tin cay)")
    try:
        res = ocr.run_ocr(data, path.name, force_ocr=a.force_ocr, do_preprocess=not a.no_preprocess)
    except (ocr.OCRUnavailable, ocr.UnsupportedFile) as e:
        sys.exit(f"OCR LOI: {e}")
    print(f"nguon={res['source']}  so dong={len(res['lines'])}  do tin cay TB={res['avg_confidence']}")
    for r in res["lines"]:
        print(f"{r['confidence']:6.1f} | {r['text']}")
    if not res["lines"]:
        sys.exit("OCR khong doc duoc dong nao: loi o buoc OCR (anh, mo hinh, tien xu ly).")

    print("\n== 2. Quy tac regex (khong LLM)")
    for k, v in rule_extract(res["text"]).items():
        print(f"{k:18} {v if v is not None else '--- khong thay'}")

    print("\n== 3. Ket qua cuoi (gom LLM neu bat) + do tin cay")
    out = extractor.extract_fields(res, use_llm=not a.no_llm)
    print(f"nguon chinh: {out['source']}")
    for k, v in out["fields"].items():
        print(f"{k:18} {str(v['value']):40} tin cay {v['confidence']:5.1f}  ({v['source']})")
    for w in out["warnings"]:
        print("CANH BAO:", w)


if __name__ == "__main__":
    main()
