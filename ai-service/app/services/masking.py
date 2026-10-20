"""Che du lieu nhay cam truoc khi gui LLM ngoai, roi khoi phuc lai trong ket qua (A7).

Che: day so dai (MST, so tai khoan, so dien thoai), email. KHONG che ten cong ty vi can trich xuat.
Bat/tat bang bien moi truong LLM_MASK (mac dinh 1).
"""
import os
import re

_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),                    # email
    re.compile(r"(?<![\d.,])\d{9,16}(?:-\d{3})?(?![\d.,])"),         # MST / STK / so dien thoai lien nhau
    re.compile(r"(?<!\d)0\d{2,3}[ .]\d{3,4}[ .]\d{3,4}(?!\d)"),      # so dien thoai co khoang cach
]


def enabled() -> bool:
    return os.getenv("LLM_MASK", "1") not in ("0", "false", "False", "")


def mask(text: str) -> tuple[str, dict[str, str]]:
    """Tra ve (van ban da che, bang token->gia tri that). Cung gia tri thi cung token."""
    table: dict[str, str] = {}
    reverse: dict[str, str] = {}

    def repl(m: re.Match) -> str:
        v = m.group(0)
        if v not in reverse:
            tok = f"[ID_{len(reverse) + 1}]"
            reverse[v], table[tok] = tok, v
        return reverse[v]

    for p in _PATTERNS:
        text = p.sub(repl, text)
    return text, table


def unmask(value, table: dict[str, str]):
    if not isinstance(value, str):
        return value
    for tok, real in table.items():
        value = value.replace(tok, real)
    return value
