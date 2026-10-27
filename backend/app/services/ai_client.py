"""Goi ai-service qua HTTP. Tach rieng de test thay the bang ham gia."""
import logging
from pathlib import Path

import httpx

from app.config import settings

log = logging.getLogger(__name__)
EXTRACT_TIMEOUT = 600  # giay


class AIServiceError(RuntimeError):
    """ai-service khong chay, bi loi, hoac tra du lieu sai."""


def extract_invoice(path: Path, filename: str) -> dict:
    """Gui file sang POST /extract. Tra ve {"fields": {ten: {"value", "confidence"}}, ...}."""
    try:
        with open(path, "rb") as f:
            r = httpx.post(f"{settings.ai_service_url}/extract", files={"file": (filename, f)},
                           data={"job_id": path.name},   # job_id = ten file da luu, de hoi tien do
                           # ai-service doc anh lan luot nen hoa don xep hang cuoi phai cho lau: cho toi da 10 phut
                           timeout=httpx.Timeout(EXTRACT_TIMEOUT, connect=10))
    except httpx.HTTPError as e:
        raise AIServiceError(f"Không gọi được dịch vụ AI: {e}") from e
    if r.status_code != 200:
        raise AIServiceError(f"Dịch vụ AI trả lỗi {r.status_code}: {r.text[:200]}")
    try:
        return r.json()["data"]
    except (ValueError, KeyError) as e:
        raise AIServiceError("Dịch vụ AI trả dữ liệu sai định dạng") from e


def get_progress(job_id: str) -> dict | None:
    """Tien do doc tai lieu {"percent", "stage"} tu ai-service. Best-effort: loi/khong co thi tra None."""
    try:
        r = httpx.get(f"{settings.ai_service_url}/progress/{job_id}", timeout=3)
        return r.json()["data"] if r.status_code == 200 else None
    except (httpx.HTTPError, ValueError, KeyError):
        return None


def normalize_vendor(name: str, candidates: list[str]) -> dict | None:
    """Best-effort: loi thi tra None, khong lam hong luong kiem tra."""
    try:
        r = httpx.post(f"{settings.ai_service_url}/normalize-vendor",
                       json={"name": name, "candidates": candidates}, timeout=10)
        r.raise_for_status()
        return r.json()["data"]
    except (httpx.HTTPError, ValueError, KeyError) as e:
        log.warning("normalize-vendor loi: %s", e)
        return None
