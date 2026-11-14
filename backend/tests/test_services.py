from datetime import date
from decimal import Decimal

from app.services.checks import check_mst, check_totals
from app.services.normalize import canonical, parse_date, parse_money, parse_rate


def test_parse_money():
    assert parse_money("4.192.668") == 4192668
    assert parse_money("4,192,668 VND") == 4192668
    assert parse_money("1100000.00") == Decimal("1100000.00")
    assert parse_money("") is None and parse_money(None) is None and parse_money("abc") is None


def test_parse_date_and_rate():
    assert parse_date("23/06/2026") == date(2026, 6, 23)
    assert parse_date("2026-06-23") == date(2026, 6, 23)
    assert parse_date("Ngay 3 thang 6 nam 2026") == date(2026, 6, 3)
    assert parse_date("31/02/2026") is None
    assert parse_rate("8%") == 8 and parse_rate("KCT") is None


def test_canonical():
    assert canonical("invoice_number", "291609") == "0291609"
    assert canonical("invoice_series", "c26 mbf") == "C26MBF"
    assert canonical("mst_seller", "0487 211 601") == "0487211601"
    assert canonical("vat_rate", "10.00") == "10"


def test_check_mst():
    assert check_mst("0487211601") and check_mst("0487211601-001") and check_mst("0487211601001")
    assert not check_mst("123") and not check_mst(None) and not check_mst("04872116AB")


def test_check_totals():
    ok, _ = check_totals(Decimal(1000), Decimal(10), Decimal(100), Decimal(1100))
    assert ok is True
    ok, issues = check_totals(Decimal(1000), Decimal(10), Decimal(100), Decimal(1200))
    assert ok is False and issues
    ok, issues = check_totals(Decimal(1000), Decimal(8), Decimal(100), Decimal(1100))  # thue suat khong khop tien thue
    assert ok is False
    assert check_totals(None, None, None, None)[0] is None


# ---- Bug 24 / 25: doc so tien moi dang va giu chu cai trong MST
import pytest as _pytest  # noqa: E402
from decimal import Decimal as _D  # noqa: E402

MONEY_CASES = [
    ("4.192.668", "4192668"), ("4,192,668", "4192668"), ("4192668", "4192668"), ("1100000.00", "1100000.00"),
    ("49,632,990.00", "49632990.00"), ("1.100.000,50", "1100000.50"), ("17,462,720.00", "17462720.00"),
    ("1.100", "1100"), ("1,100", "1100"), ("1,5", "1.5"), ("12.5", "12.5"), ("  3.882.100 đ", "3882100"),
    ("1.234.567 VND", "1234567"), ("0", "0"),
]


@_pytest.mark.parametrize("raw,want", MONEY_CASES)
def test_parse_money_formats(raw, want):
    from app.services.normalize import parse_money
    assert parse_money(raw) == _D(want)


def test_parse_money_unreadable():
    from app.services.normalize import parse_money
    assert parse_money("") is None and parse_money("abc") is None and parse_money(None) is None


def test_canonical_money_no_x100():
    from app.services.normalize import canonical
    assert canonical("total_amount", "49,632,990.00") == "49632990"      # tung ra 4963299000


def test_mst_text_only_is_rejected():
    from app.services.normalize import canonical
    assert canonical("mst_seller", "chưa có") is None and canonical("mst_seller", "abc") is None


def test_mst_keeps_letters_so_error_is_visible():
    from app.services.normalize import canonical
    assert canonical("mst_seller", "0172A69957") == "0172A69957"           # tung bi bien thanh 017269957
    assert canonical("mst_seller", "0487 211 601") == "0487211601"
    assert canonical("mst_seller", "0100109106-001") == "0100109106-001"


def test_duplicate_check_reports_when_it_could_not_run():
    from types import SimpleNamespace
    from app.services import checks
    full = SimpleNamespace(invoice_series="C26MBF", invoice_number="1", mst_seller="0487211601")
    assert checks.can_check_duplicate(full) is True
    for missing in ("invoice_series", "invoice_number", "mst_seller"):
        inv = SimpleNamespace(**{**full.__dict__, missing: None})
        assert checks.can_check_duplicate(inv) is False
