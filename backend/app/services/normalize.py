"""Ham chuan hoa gia tri (tien, ngay, thue suat, MST) dung chung cho XML, AI va API (Goi A).

Quy uoc: ten truong (field_name) la tieng Anh, trung voi cot cua bang invoices va hop dong API.
"""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

# Cac truong AI/XML tra ve, theo dung ten cot trong bang invoices
FIELD_NAMES = [
    "invoice_series", "invoice_number", "invoice_date", "seller_name", "mst_seller",
    "total_before_tax", "vat_rate", "vat_amount", "total_amount",
]
MONEY_FIELDS = {"total_before_tax", "vat_amount", "total_amount"}


def parse_money(value) -> Decimal | None:
    """'4.192.668' / '4,192,668' / '4192668' / '1100000.00' -> Decimal. Tra None neu khong doc duoc."""
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    s = str(value).strip()
    if not s:
        return None
    s = re.sub(r"(?i)\s*(vnd|vnđ|đ|dong|đồng)\s*$", "", s).strip()
    if re.fullmatch(r"\d+\.\d{1,2}", s):  # '1100000.00': dau cham la dau thap phan
        return Decimal(s)
    digits = re.sub(r"[^\d]", "", s)
    if not digits:
        return None
    return Decimal(digits)


def parse_rate(value) -> Decimal | None:
    """'8%' / '8' / '10.00' -> Decimal. 'KCT', 'KKKNT'... -> None."""
    if value is None:
        return None
    s = str(value).strip().replace(",", ".").rstrip("%").strip()
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def parse_date(value) -> date | None:
    """'23/06/2026', '2026-06-23', '23-06-2026', 'Ngay 23 thang 06 nam 2026' -> date."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = (re.search(r"(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4})", s)
             or re.search(r"(\d{1,2})\D+(\d{1,2})\D+(\d{4})", s))
        if not m:
            return None
        d, mo, y = map(int, m.groups())
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def clean_mst(value) -> str | None:
    """Giu chu so va dau '-'. '0487 211 601' -> '0487211601'."""
    if value is None:
        return None
    s = re.sub(r"[^\d\-]", "", str(value))
    return s.strip("-") or None


def clean_text(value) -> str | None:
    if value is None:
        return None
    s = re.sub(r"\s+", " ", str(value)).strip()
    return s or None


def money_str(d: Decimal | None) -> str | None:
    """Decimal -> chuoi so nguyen neu khong co phan le (de luu extracted_value)."""
    if d is None:
        return None
    return str(int(d)) if d == d.to_integral_value() else format(d, "f")


def rate_str(d: Decimal | None) -> str | None:
    if d is None:
        return None
    return str(int(d)) if d == d.to_integral_value() else format(d.normalize(), "f")


def canonical(name: str, value) -> str | None:
    """Dua gia tri ve dang chuan de luu extracted_value (chuoi)."""
    if value is None:
        return None
    if name in MONEY_FIELDS:
        return money_str(parse_money(value))
    if name == "vat_rate":
        return rate_str(parse_rate(value))
    if name == "invoice_date":
        d = parse_date(value)
        return d.isoformat() if d else None
    if name == "mst_seller":
        return clean_mst(value)
    if name == "invoice_series":
        t = clean_text(value)
        return t.upper().replace(" ", "") if t else None
    if name == "invoice_number":
        t = clean_text(value)
        if t and t.isdigit():
            return t.zfill(7)
        return t
    return clean_text(value)


def to_column(name: str, value):
    """Chuoi da chuan hoa -> kieu du lieu cua cot trong bang invoices."""
    if value is None:
        return None
    if name in MONEY_FIELDS:
        return parse_money(value)
    if name == "vat_rate":
        return parse_rate(value)
    if name == "invoice_date":
        return parse_date(value)
    return str(value)
