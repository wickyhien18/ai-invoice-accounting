"""Goi POST /classify-gl cua ai-service (B5/B6). Tach rieng de test thay bang ham gia."""
import logging

import httpx

from app.config import settings

log = logging.getLogger(__name__)


def classify_gl(payload: dict) -> dict | None:
    """Best-effort: ai-service tat/loi thi tra None de noi goi dung quy tac mac dinh, khong lam hong man hinh dinh khoan."""
    try:
        r = httpx.post(f"{settings.ai_service_url}/classify-gl", json=payload, timeout=60)  # Gemini co the cho ~13 s gian cach
        r.raise_for_status()
        return r.json()["data"]
    except (httpx.HTTPError, ValueError, KeyError) as e:
        log.warning("classify-gl loi: %s", e)
        return None
