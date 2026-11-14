"""Chuan hoa gia tri truong hoa don o ai-service (cung quy uoc voi backend/app/services/normalize.py).

Ten truong trung ten cot bang invoices: invoice_series, invoice_number, invoice_date, seller_name,
mst_seller, total_before_tax, vat_rate, vat_amount, total_amount.
"""
import re
from datetime import date
from decimal import Decimal, InvalidOperation

FIELD_NAMES = ["invoice_series", "invoice_number", "invoice_date", "seller_name", "mst_seller",
               "total_before_tax", "vat_rate", "vat_amount", "total_amount"]
MONEY = {"total_before_tax", "vat_amount", "total_amount"}


def parse_money(value) -> Decimal | None:
    """Doc so tien o moi dang: '4.192.668', '4,192,668', '49,632,990.00', '1.100.000,50', '1100000.00' -> Decimal.

    Dau phan cach CUOI CUNG la dau thap phan khi co tu 1-2 chu so dung sau no; dau con lai la phan nghin.
    Chi co mot loai dau, xuat hien 1 lan, theo sau dung 3 chu so ('1.100', '1,100') thi la phan nghin (kieu Viet Nam).
    Tra None neu khong doc duoc."""
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    s = str(value).strip()
    if not s:
        return None
    s = re.sub(r"(?i)\s*(vnd|vnđ|đ|dong|đồng)\s*$", "", s).strip()
    s = re.sub(r"[^\d.,]", "", s)
    if not re.search(r"\d", s):
        return None
    last = max(s.rfind("."), s.rfind(","))
    if last == -1:
        return Decimal(s)
    head, sep, tail = s[:last], s[last], s[last + 1:]
    other = "," if sep == "." else "."
    if other in head or (sep not in head and len(tail) in (1, 2)):
        is_decimal = len(tail) in (1, 2)          # '49,632,990.00' / '1.100.000,50' / '1100000.00'
    else:
        is_decimal = False                        # '4.192.668' / '1,100' / '1.100'
    if is_decimal:
        return Decimal(re.sub(r"[.,]", "", head) + "." + tail)
    return Decimal(re.sub(r"[.,]", "", s))


def parse_date(v) -> date | None:
    if v is None:
        return None
    s = str(v)
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = re.search(r"(\d{1,2})\D{1,25}?(\d{1,2})\D{1,25}?(\d{4})", s)
        if not m:
            return None
        d, mo, y = map(int, m.groups())
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def parse_rate(v) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v).strip().replace(",", ".").rstrip("%").strip())
    except InvalidOperation:
        return None


def _int_str(d: Decimal) -> str:
    return str(int(d)) if d == d.to_integral_value() else format(d.normalize(), "f")


def canonical(name: str, v) -> str | None:
    """Dua ve chuoi chuan; None neu rong hoac khong doc duoc."""
    if v is None or str(v).strip() == "":
        return None
    if name in MONEY:
        d = parse_money(v)
        return None if d is None else _int_str(d)
    if name == "vat_rate":
        d = parse_rate(v)
        return None if d is None else _int_str(d)
    if name == "invoice_date":
        d = parse_date(v)
        return d.isoformat() if d else None
    if name == "mst_seller":
        # giu chu cai (Bug 25): MST sai dinh dang phai hien nguyen, khong bi bien thanh day so ngan hon
        m = re.sub(r"[^0-9A-Za-z\-]", "", str(v)).upper().strip("-")
        return m if sum(c.isdigit() for c in m) >= 5 else None   # chu thuan khong phai MST
    if name == "invoice_series":
        s = re.sub(r"\s+", "", str(v)).upper()
        return s[1:] if len(s) == 7 and s[0].isdigit() else (s or None)  # '1C26TAA' -> 'C26TAA'
    if name == "invoice_number":
        s = re.sub(r"\s+", "", str(v))
        return s.zfill(7) if s.isdigit() else (s or None)
    return re.sub(r"\s+", " ", str(v)).strip() or None
