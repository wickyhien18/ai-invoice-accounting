"""A5: doc truc tiep XML hoa don dien tu, khong qua OCR.

Ho tro cau truc HDon/DLHDon (TTChung, NDHDon/NBan, TToan) nhu data_test/xml. Bo qua namespace
de doc duoc ca file that. Dung defusedxml de chan XXE / billion laughs.
"""
from collections import Counter

from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

from app.services.normalize import FIELD_NAMES, canonical


class XmlInvoiceError(ValueError):
    """File khong phai XML hoa don hop le."""


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find(root, *path):
    """Tim phan tu dau tien theo duong dan ten (bo namespace), tim o moi do sau."""
    nodes = [root]
    for name in path:
        nxt = []
        for n in nodes:
            nxt.extend(c for c in n.iter() if c is not n and _local(c.tag) == name)
        if not nxt:
            return None
        nodes = nxt
    return nodes[0]


def _text(root, *path):
    n = _find(root, *path)
    return n.text.strip() if n is not None and n.text and n.text.strip() else None


def parse_invoice_xml(data: bytes) -> dict:
    """Tra ve {"fields": {ten: {"value", "confidence"}}, "warnings": [...]}."""
    try:
        root = ET.fromstring(data)
    except (ET.ParseError, DefusedXmlException, ValueError) as e:
        raise XmlInvoiceError(f"File XML không hợp lệ: {e}") from e
    if _local(root.tag) != "HDon":
        raise XmlInvoiceError("Không phải hóa đơn điện tử (thiếu thẻ gốc HDon)")

    warnings: list[str] = []
    raw = {
        "invoice_series": _text(root, "TTChung", "KHHDon"),
        "invoice_number": _text(root, "TTChung", "SHDon"),
        "invoice_date": _text(root, "TTChung", "NLap"),
        "seller_name": _text(root, "NBan", "Ten"),
        "mst_seller": _text(root, "NBan", "MST"),
        "total_before_tax": _text(root, "TToan", "TgTCThue"),
        "vat_amount": _text(root, "TToan", "TgTThue"),
        "total_amount": _text(root, "TToan", "TgTTTBSo"),
    }
    # Thue suat: lay tu cac dong hang; neu nhieu muc khac nhau thi de trong va canh bao
    rates = [n.text.strip() for n in root.iter() if _local(n.tag) == "TSuat" and n.text and n.text.strip()]
    if rates:
        counts = Counter(rates)
        if len(counts) > 1:
            warnings.append(f"Hoa don co nhieu muc thue suat {sorted(counts)}; can nhap tay thue suat chung")
            raw["vat_rate"] = None
        else:
            raw["vat_rate"] = rates[0]
    else:
        raw["vat_rate"] = None

    fields = {}
    for name in FIELD_NAMES:
        value = canonical(name, raw.get(name))
        if value is None:
            warnings.append(f"Thieu truong {name} trong XML")
            fields[name] = {"value": None, "confidence": 0}
        else:
            # XML la du lieu co cau truc nen tin cay toi da; van de kiem tra so hoc o buoc /check
            fields[name] = {"value": value, "confidence": 100}
    return {"fields": fields, "warnings": warnings}
