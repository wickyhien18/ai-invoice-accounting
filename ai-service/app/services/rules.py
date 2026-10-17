"""Doc cac truong hoa don bang quy tac regex tu van ban OCR, CHIU LOI OCR.

Van ban OCR cua anh nhieu thuong: mat dau tieng Viet, mat dau ':', nham O/0 va l/1, nhan dung o dong
ke tiep. Vi vay moi nhan ('Ma so thue', 'Tong tien thanh toan'...) duoc so khop tren ban DA BO DAU,
khong phan biet hoa thuong, dau ':' tuy chon; so tien duoc sua cac nham ky tu pho bien.
Gia tri tra ve van la chuoi chua chuan hoa (extractor goi canonical sau).
"""
import re
import unicodedata

from app.services.fields import FIELD_NAMES, canonical, parse_date


def fold(text: str) -> str:
    """Bo dau, giu nguyen DO DAI tung ky tu (de lay lai ten goc theo chi so). 'đ' -> 'd'."""
    text = unicodedata.normalize("NFC", text).replace("đ", "d").replace("Đ", "D")
    return "".join(unicodedata.normalize("NFD", c)[0] for c in text)


_SEP = r"[:：;.]?"
_GAP = r"[^:\d\n]{0,30}"
_NUM = r"([\dOoIl](?:[\dOoIl.,]*[\dOoIl])?)(?![A-Za-z])"   # chap nhan O/o/I/l bi doc nham thanh so


def _digits(tok: str) -> str:
    """'3.882.1OO' -> '3.882.100'."""
    return tok.translate(str.maketrans("OoIl", "0011"))


def _money(rx: re.Pattern, folded: str) -> str | None:
    for m in rx.finditer(folded):
        raw = m.group(1)
        tok = _digits(raw)
        # phai co it nhat mot chu so THAT (tranh bat 'Online', 'lol'...) va chi con chu so, dau cham, dau phay
        if re.search(r"\d", raw) and re.fullmatch(r"[\d.,]+", tok):
            return tok
    return None


_RX = {
    "series": re.compile(r"(?:ky\s*hieu|serial)" + _GAP + _SEP + r"\s*([0-9]?[A-Z]\d{2}[A-Z]{2,3})\b", re.I),
    "series_any": re.compile(r"(?<![A-Za-z0-9])([0-9]?[CK]\d{2}[A-Z]{3})(?![A-Za-z0-9])"),
    "number": re.compile(r"(?<![a-z])(?<!mau )(?:so|no)(?:\s*hoa\s*don)?\s*(?:\([^)]*\))?\s*[:：;.]\s*(\d{1,8})(?!\d)", re.I),
    "number_marker": re.compile(r"\(\s*No\.?\s*\)\s*[:：;.]?\s*(\d{1,8})(?!\d)", re.I),  # 'So (No.) 0291609' khong co ':'
    # 'So 0291609' mat ':' : chi nhan 6-8 chu so de khong nham voi so nha ('So 240 duong ...')
    "number_loose": re.compile(r"(?<![a-z])(?<!mau )so\s*[:：;.]?\s*(\d{6,8})(?!\d)", re.I),
    "mst": re.compile(r"(?:ma\s*so\s*thue|mst|tax\s*code)" + _GAP + _SEP + r"\s*(\d[\d \-]{8,16}\d)", re.I),
    "mst_any": re.compile(r"(?<![\d.,])(\d{10}(?:-\d{3})?)(?![\d.,])"),
    "date": re.compile(r"ngay" + r"\D{0,15}(\d{1,2})\D{1,25}?(\d{1,2})\D{1,25}?(\d{4})", re.I),
    "date_any": re.compile(r"(?<!\d)(\d{1,2}\s*[/.\-]\s*\d{1,2}\s*[/.\-]\s*\d{4})(?!\d)"),
    "before": re.compile(r"(?:cong\s*tien\s*hang|tong\s*tien\s*chua\s*(?:co\s*)?thue|thanh\s*tien\s*chua\s*thue)"
                         + _GAP + _SEP + r"\s*" + _NUM, re.I),
    "rate": re.compile(r"thue\s*suat" + _GAP + _SEP + r"\s*(\d{1,2}(?:[.,]\d)?)\s*(%?)", re.I),
    # 'Tien thue' phai di kem GTGT/VAT hoac dau ':' de khong nham voi mat hang 'Tien thue (thuê) phong hop'
    "vat": re.compile(r"tien\s*thue(?=\s*(?:gtgt|\(?\s*vat|[:：]))(?:\s*gtgt)?" + _GAP + _SEP + r"\s*" + _NUM, re.I),
    "total": re.compile(r"(?:tong\s*cong\s*tien\s*thanh\s*toan|tong\s*tien\s*thanh\s*toan|tong\s*cong\s*thanh\s*toan"
                        r"|tong\s*thanh\s*toan)" + _GAP + _SEP + r"\s*" + _NUM, re.I),
    "total_weak": re.compile(r"tong\s*cong" + _GAP + _SEP + r"\s*" + _NUM, re.I),
    "company": re.compile(r"^\W*(cong\s*ty|cty|doanh\s*nghiep|cua\s*hang|ho\s*kinh\s*doanh|tap\s*doan|tong\s*cong\s*ty|chi\s*nhanh)\b", re.I),
    "seller_label": re.compile(r"don\s*vi\s*ban\s*hang[^:\n]*[:：]\s*(.+)", re.I),
}


def rule_extract(text: str) -> dict[str, str | None]:
    """Tra ve {ten_truong: gia_tri_da_chuan_hoa | None}."""
    text = unicodedata.normalize("NFC", text)
    folded = fold(text)
    lines, flines = text.split("\n"), folded.split("\n")
    out: dict[str, str | None] = {n: None for n in FIELD_NAMES}

    # ky hieu: theo nhan, neu khong co thi tim mau C26XXX / K26XXX o bat ky dau
    m = _RX["series"].search(folded) or _RX["series_any"].search(folded)
    if m:
        out["invoice_series"] = canonical("invoice_series", m.group(1))

    # so hoa don: lay ung vien co nhieu chu so nhat (tranh 'Mau so (Form): 1')
    cands = [c.group(1) for k in ("number", "number_marker", "number_loose") for c in _RX[k].finditer(folded)]
    if cands:
        out["invoice_number"] = canonical("invoice_number", max(cands, key=lambda s: (len(s), -cands.index(s))))

    # ngay lap
    m = _RX["date"].search(folded)
    if m:
        out["invoice_date"] = canonical("invoice_date", "/".join(m.groups()))
    else:
        m = _RX["date_any"].search(folded)
        if m:
            out["invoice_date"] = canonical("invoice_date", re.sub(r"\s*([/.\-])\s*", "/", m.group(1)))
    if out["invoice_date"] and parse_date(out["invoice_date"]) is None:
        out["invoice_date"] = None

    # MST nguoi ban = MST dau tien trong van ban
    mst_line = next((i for i, ln in enumerate(flines) if _RX["mst"].search(ln)), None)
    if mst_line is not None:
        out["mst_seller"] = canonical("mst_seller", _RX["mst"].search(flines[mst_line]).group(1))
    else:
        m = _RX["mst_any"].search(folded)
        if m:
            out["mst_seller"] = canonical("mst_seller", m.group(1))

    # ten nguoi ban: dong co dang ten cong ty nam TRUOC dong MST dau tien (lay ten goc co dau)
    m = _RX["seller_label"].search(folded)
    if m:
        out["seller_name"] = canonical("seller_name", text[m.start(1):m.end(1)])
    else:
        end = mst_line if mst_line is not None else len(lines)
        cand = [lines[i].strip() for i in range(min(end, len(lines))) if _RX["company"].match(flines[i].strip())]
        if cand:
            out["seller_name"] = canonical("seller_name", cand[-1])
        elif mst_line is not None and mst_line > 0:
            above = lines[mst_line - 1].strip()           # du phong: dong ngay tren dong MST
            if len(above) >= 8 and not _RX["mst"].search(fold(above)):
                out["seller_name"] = canonical("seller_name", above)

    # tien
    out["total_before_tax"] = canonical("total_before_tax", _money(_RX["before"], folded))
    out["vat_amount"] = canonical("vat_amount", _money(_RX["vat"], folded))
    out["total_amount"] = canonical("total_amount", _money(_RX["total"], folded) or _money(_RX["total_weak"], folded))

    # thue suat: co dau % thi nhan; khong co % thi chi nhan 0/5/8/10 (tranh bat nham so khac)
    for m in _RX["rate"].finditer(folded):
        val = m.group(1).replace(",", ".")
        if m.group(2) or val in ("0", "5", "8", "10"):
            out["vat_rate"] = canonical("vat_rate", val)
            break
    return out
