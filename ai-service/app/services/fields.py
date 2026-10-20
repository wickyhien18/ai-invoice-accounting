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


def parse_money(v) -> Decimal | None:
    if v is None:
        return None
    s = str(v).strip()
    if re.fullmatch(r"\d+\.\d{1,2}", s):
        return Decimal(s)
    digits = re.sub(r"[^\d]", "", s)
    return Decimal(digits) if digits else None


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
        return re.sub(r"[^\d\-]", "", str(v)).strip("-") or None
    if name == "invoice_series":
        s = re.sub(r"\s+", "", str(v)).upper()
        return s[1:] if len(s) == 7 and s[0].isdigit() else (s or None)  # '1C26TAA' -> 'C26TAA'
    if name == "invoice_number":
        s = re.sub(r"\s+", "", str(v))
        return s.zfill(7) if s.isdigit() else (s or None)
    return re.sub(r"\s+", " ", str(v)).strip() or None
