"""Tro giup cho cac script trong tools/: tu dung Python cua venv ai-service neu Python dang chay thieu thu vien.

Nho do ban chay duoc tu thu muc goc du an bang bat ky Python nao (ke ca khi chua kich hoat venv):
    python tools/debug_ocr.py data_test/images/HD001.png

Tim venv o ai-service/venv (Windows: Scripts/python.exe, Linux/macOS: bin/python), dung ten thu muc nhu SETUP.md.
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _venv(service: str):
    d = ROOT / service / "venv"
    for rel in ("Scripts/python.exe", "bin/python"):
        if (d / rel).exists():
            return d, d / rel
    return d, None


def ensure_venv(needs: tuple[str, ...], service: str = "ai-service") -> None:
    """Neu Python hien tai du cac module trong `needs` thi chay tiep; neu khong thi chay lai chinh script nay
    bang Python cua <service>/venv (giu nguyen tham so). Khong co venv thi in huong dan roi thoat."""
    if os.environ.get("INVOICE_TOOLS_CHILD"):          # da la tien trinh con: khong chuyen tiep nua
        return
    missing = [m for m in needs if importlib.util.find_spec(m) is None]
    if not missing:
        return
    venv_dir, py = _venv(service)
    if py is None:
        sys.exit(
            f"Python hien tai thieu thu vien: {', '.join(missing)}, va khong thay {venv_dir}.\n"
            f"Tao venv mot lan (xem SETUP.md muc 3.1):\n"
            f"    cd {service}\n"
            f"    python -m venv venv\n"
            f"    venv\\Scripts\\activate        (Linux/macOS: source venv/bin/activate)\n"
            f"    pip install -r requirements.txt\n"
            f"Sau do chay lai lenh nay tu thu muc goc, khong can kich hoat venv."
        )
    print(f"[tools] Dung Python cua {venv_dir.relative_to(ROOT)} (Python hien tai thieu: {', '.join(missing)})\n",
          flush=True)
    env = dict(os.environ, INVOICE_TOOLS_CHILD="1")
    sys.exit(subprocess.call([str(py), *sys.argv], env=env))
