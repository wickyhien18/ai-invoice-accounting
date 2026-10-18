"""Module goi LLM dung chung (A7, Hien viet; Khanh dung o B6).

    from app.llm import generate_json, LLMUnavailable
    data = generate_json("Hay tra JSON {...}", schema={...})   # -> dict

- Model lay tu LLM_MODEL, khoa tu GEMINI_API_KEY (file .env goc).
- Tra ve dict da parse. Loi tam thoi (503, JSON sai) thi thu lai toi da LLM_MAX_ATTEMPTS lan (mac dinh 2).
- TIET KIEM HAN MUC (ban mien phi: ~5 yeu cau/phut, ~20 yeu cau/ngay, KHONG phai gioi han token):
    * cache: cung noi dung + cung model thi dung lai ket qua cu, khong goi Gemini (LLM_CACHE=0 de tat)
    * gian cach: toi thieu LLM_MIN_INTERVAL giay giua hai lan goi (mac dinh 13 s -> khong vuot 5/phut)
    * ngan sach ngay: toi da LLM_DAILY_LIMIT lan goi/ngay (mac dinh 18, 0 = khong gioi han); het thi
      raise LLMUnavailable de noi goi chuyen sang quy tac regex thay vi bi 429
- LLMUnavailable: khong co khoa, khoa sai, het han muc (429) hoac may chu Google loi lien tiep.
  Noi goi nen bat loi nay de chuyen sang cach khong dung LLM (xem services/extractor.py).
- Rieng tu: ban Gemini mien phi co the dung du lieu de cai tien san pham -> chi gui hoa don gia/da che.
  Dung services.masking.mask() truoc khi gui du lieu that.
"""
import hashlib
import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger(__name__)


class LLMUnavailable(RuntimeError):
    """Khong co API key, key sai, het han muc hoac may chu LLM khong tra loi."""


class LLMError(RuntimeError):
    """LLM tra loi nhung khong parse duoc thanh JSON."""


class _Retryable(Exception):
    pass


# --------------------------------------------------------------------------- tiet kiem han muc
_CACHE_DIR = Path(os.getenv("LLM_CACHE_DIR", Path(__file__).resolve().parents[1] / ".cache"))
_lock = threading.Lock()
_last_call = 0.0


def _num(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


def _today() -> str:
    """Ngay theo gio Thai Binh Duong: han muc ngay cua Google dat lai luc nua dem o day."""
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("America/Los_Angeles"))
    except Exception:  # Windows chua cai tzdata
        now = datetime.now(timezone(timedelta(hours=-8)))
    return now.strftime("%Y-%m-%d")


def _usage_file() -> Path:
    return Path(os.getenv("LLM_USAGE_FILE", _CACHE_DIR / "llm_usage.json"))


def usage() -> dict:
    """{'day': 'YYYY-MM-DD', 'used': so lan da goi hom nay}."""
    try:
        d = json.loads(_usage_file().read_text(encoding="utf-8"))
        if d.get("day") == _today():
            return {"day": d["day"], "used": int(d.get("used", 0))}
    except (OSError, ValueError, TypeError):
        pass
    return {"day": _today(), "used": 0}


def set_usage(used: int) -> None:
    f = _usage_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"day": _today(), "used": int(used)}), encoding="utf-8")


def _reserve_call() -> None:
    """Giu mot luot goi: kiem tra ngan sach ngay, doi cho du gian cach toi thieu, roi tinh them 1 luot.
    Moi lan GUI yeu cau deu tinh (ke ca lan loi) vi Google cung tinh nhu vay."""
    global _last_call
    with _lock:
        limit = int(_num("LLM_DAILY_LIMIT", 18))
        u = usage()
        if limit > 0 and u["used"] >= limit:
            raise LLMUnavailable(
                f"Da dung het {limit} luot Gemini hom nay (LLM_DAILY_LIMIT); dung quy tac regex. "
                "Han muc ngay cua Google thuong dat lai luc nua dem gio Thai Binh Duong (khoang 14-15h gio Viet Nam).")
        wait = _last_call + _num("LLM_MIN_INTERVAL", 13) - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()
        try:
            set_usage(u["used"] + 1)
        except OSError as e:
            log.warning("Khong ghi duoc so luot Gemini da dung: %s", e)


def _cache_path(model: str, prompt: str) -> Path:
    return _CACHE_DIR / "llm" / (hashlib.sha256(f"{model}\n{prompt}".encode()).hexdigest() + ".json")


def _cache_get(model: str, prompt: str) -> dict | None:
    if os.getenv("LLM_CACHE", "1") == "0":
        return None
    try:
        data = json.loads(_cache_path(model, prompt).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _cache_put(model: str, prompt: str, data: dict) -> None:
    if os.getenv("LLM_CACHE", "1") == "0":
        return
    try:
        f = _cache_path(model, prompt)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError as e:
        log.warning("Khong ghi duoc cache LLM: %s", e)


def _call_model(prompt: str, model: str, api_key: str) -> str:
    """Cho DUY NHAT cham vao SDK google-genai (test thay ham nay)."""
    from google import genai
    from google.genai import errors, types

    client = genai.Client(api_key=api_key)
    try:
        resp = client.models.generate_content(
            model=model, contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0),
        )
    except errors.APIError as e:
        code = getattr(e, "code", None)
        if code == 429:
            raise LLMUnavailable("Het han muc Gemini (429). Doi mot luc hoac doi khoa khac.") from e
        if code in (401, 403):
            raise LLMUnavailable(f"GEMINI_API_KEY bi tu choi ({code})") from e
        if code and code >= 500:
            raise _Retryable(str(e)) from e
        raise LLMError(f"Gemini loi {code}: {e}") from e
    return resp.text or ""


def _parse(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)  # go rao ```json neu model them vao
    try:
        data = json.loads(t)
    except json.JSONDecodeError as e:
        raise LLMError(f"LLM khong tra JSON hop le: {t[:120]!r}") from e
    if not isinstance(data, dict):
        raise LLMError("LLM tra JSON khong phai object")
    return data


def generate_json(prompt: str, schema: dict | None = None) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise LLMUnavailable("Chua dat GEMINI_API_KEY trong .env")
    model = os.getenv("LLM_MODEL", "gemini-3.8-flash")
    if schema:
        prompt += "\n\nChi tra ve DUY NHAT mot JSON dung cau truc sau:\n" + json.dumps(schema, ensure_ascii=False)
    cached = _cache_get(model, prompt)
    if cached is not None:
        log.info("LLM: dung ket qua da luu (khong goi Gemini)")
        return cached
    last: Exception | None = None
    attempts = max(1, int(_num("LLM_MAX_ATTEMPTS", 2)))
    for attempt in range(attempts):
        try:
            _reserve_call()
            data = _parse(_call_model(prompt, model, api_key))
            _cache_put(model, prompt, data)
            return data
        except (_Retryable, LLMError) as e:
            last = e
            log.warning("LLM lan %d that bai: %s", attempt + 1, e)
            time.sleep(2.0 * (attempt + 1))     # 503 do qua tai: doi lau hon truoc khi thu lai
    if isinstance(last, _Retryable):
        raise LLMUnavailable(f"May chu Gemini loi lien tiep: {last}") from last
    raise last  # type: ignore[misc]
