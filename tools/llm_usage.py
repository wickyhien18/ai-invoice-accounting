#!/usr/bin/env python3
"""Xem / chinh so luot Gemini da dung hom nay (de tiet kiem han muc mien phi).

    python tools/llm_usage.py            # xem so luot da dung hom nay va gioi han
    python tools/llm_usage.py set 17     # dat lai so luot da dung (vd: khop voi so tren Google AI Studio)
    python tools/llm_usage.py clear-cache  # xoa cache ket qua LLM

Chi dung thu vien chuan, chay bang Python nao cung duoc.
"""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai-service"))
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:  # khong co python-dotenv: doc bien moi truong san co
    pass

from app import llm  # noqa: E402

args = sys.argv[1:]
if args[:1] == ["set"] and len(args) == 2 and args[1].isdigit():
    llm.set_usage(int(args[1]))
elif args[:1] == ["clear-cache"]:
    shutil.rmtree(llm._CACHE_DIR / "llm", ignore_errors=True)
    print("Da xoa cache LLM.")
elif args:
    sys.exit(__doc__)
u = llm.usage()
limit = int(os.getenv("LLM_DAILY_LIMIT", 18))
print(f"Ngay (gio Thai Binh Duong): {u['day']}   da dung: {u['used']}   gioi han LLM_DAILY_LIMIT: {limit or 'khong'}")
