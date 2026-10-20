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
