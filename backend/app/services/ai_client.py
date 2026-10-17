"""Goi ai-service qua HTTP. Tach rieng de test thay the bang ham gia."""
import logging
from pathlib import Path

import httpx

from app.config import settings

log = logging.getLogger(__name__)


class AIServiceError(RuntimeError):
    """ai-service khong chay, bi loi, hoac tra du lieu sai."""


def extract_invoice(path: Path, filename: str) -> dict:
    """Gui file sang POST /extract. Tra ve {"fields": {ten: {"value", "confidence"}}, ...}."""
    try:
        with open(path, "rb") as f:
            r = httpx.post(f"{settings.ai_service_url}/extract", files={"file": (filename, f)}, timeout=180)
    except httpx.HTTPError as e:
        raise AIServiceError(f"Khong goi duoc ai-service: {e}") from e
    if r.status_code != 200:
        raise AIServiceError(f"ai-service tra {r.status_code}: {r.text[:200]}")
    try:
        return r.json()["data"]
    except (ValueError, KeyError) as e:
        raise AIServiceError("ai-service tra du lieu sai dinh dang") from e


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
