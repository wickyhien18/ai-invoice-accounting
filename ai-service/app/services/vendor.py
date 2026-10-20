"""A8: chuan hoa ten nguoi ban bang RapidFuzz de gop cac cach viet khac nhau cua cung mot cong ty."""
import re
import unicodedata

from rapidfuzz import fuzz, process

THRESHOLD = 88.0
# dang phap ly: bo di khi so sanh de 'CTY TNHH ABC' khop 'Cong ty TNHH ABC'
_LEGAL = {"cong", "ty", "cty", "tnhh", "cp", "co", "phan", "mtv", "mot", "thanh", "vien", "dntn",
          "doanh", "nghiep", "tu", "nhan", "jsc", "ltd", "company", "hkd", "ho", "kinh"}


def strip_accents(s: str) -> str:
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def normalize_key(name: str) -> str:
    s = strip_accents(name).casefold()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    tokens = [t for t in s.split() if t not in _LEGAL]
    return " ".join(tokens) or " ".join(s.split())


def normalize_vendor(name: str, candidates: list[str]) -> dict:
    """canonical = ten da biet giong nhat (neu >= nguong), nguoc lai la chinh ten da lam sach khoang trang."""
    cleaned = " ".join(name.split())
    key = normalize_key(cleaned)
    result = {"canonical": cleaned, "score": 0.0, "matched": False, "key": key, "alternatives": []}
    pool = {c: normalize_key(c) for c in dict.fromkeys(candidates) if c and c.strip()}
    if not pool or not key:
        return result
    ranked = process.extract(key, pool, scorer=fuzz.token_sort_ratio, limit=3)  # (key, score, original)
    result["alternatives"] = [{"name": orig, "score": round(score, 1)} for _, score, orig in ranked]
    _, score, best = ranked[0]
    result["score"] = round(score, 1)
    if score >= THRESHOLD:
        result["canonical"], result["matched"] = best, True
    return result
