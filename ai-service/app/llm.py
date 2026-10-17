"""Module goi LLM dung chung (A7, Hien viet; Khanh dung o B6).

    from app.llm import generate_json, LLMUnavailable
    data = generate_json("Hay tra JSON {...}", schema={...})   # -> dict

- Model lay tu LLM_MODEL, khoa tu GEMINI_API_KEY (file .env goc).
- Tra ve dict da parse. Neu model tra sai JSON thi thu lai toi da 3 lan.
- LLMUnavailable: khong co khoa, khoa sai, het han muc (429) hoac may chu Google loi lien tiep.
  Noi goi nen bat loi nay de chuyen sang cach khong dung LLM (xem services/extractor.py).
- Rieng tu: ban Gemini mien phi co the dung du lieu de cai tien san pham -> chi gui hoa don gia/da che.
  Dung services.masking.mask() truoc khi gui du lieu that.
"""
import json
import logging
import os
import re
import time

log = logging.getLogger(__name__)


class LLMUnavailable(RuntimeError):
    """Khong co API key, key sai, het han muc hoac may chu LLM khong tra loi."""


class LLMError(RuntimeError):
    """LLM tra loi nhung khong parse duoc thanh JSON."""


class _Retryable(Exception):
    pass


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
    model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    if schema:
        prompt += "\n\nChi tra ve DUY NHAT mot JSON dung cau truc sau:\n" + json.dumps(schema, ensure_ascii=False)
    last: Exception | None = None
    for attempt in range(3):
        try:
            return _parse(_call_model(prompt, model, api_key))
        except (_Retryable, LLMError) as e:
            last = e
            log.warning("LLM lan %d that bai: %s", attempt + 1, e)
            time.sleep(0.5 * (attempt + 1))
    if isinstance(last, _Retryable):
        raise LLMUnavailable(f"May chu Gemini loi lien tiep: {last}") from last
    raise last  # type: ignore[misc]
