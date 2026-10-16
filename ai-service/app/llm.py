"""Module goi LLM dung chung (A7, Hien viet; Khanh dung o B6).

Hien chi la KHUNG: ham generate_json da co chu ky on dinh de nguoi khac goi duoc ngay.
Khi A7 xong se goi Gemini that bang google-genai (GEMINI_API_KEY, LLM_MODEL trong .env).
Luu y quyen rieng tu: ban Gemini mien phi co the dung du lieu de cai tien san pham -> chi gui hoa don gia/da che.
"""
import os


class LLMUnavailable(RuntimeError):
    """Khong co API key hoac het han muc."""


def generate_json(prompt: str, schema: dict | None = None) -> dict:
    if not os.getenv("GEMINI_API_KEY"):
        raise LLMUnavailable("Chua dat GEMINI_API_KEY trong .env")
    raise NotImplementedError("A7: goi Gemini that o day (model lay tu LLM_MODEL)")
