"""HOP DONG API (mock-first). Moi endpoint tra du lieu mau + "mock": true.

Quy tac nhom: khi lam xong that mot endpoint, XOA no khoi file nay va chuyen sang router rieng
(vd app/routers/invoices.py). Frontend dung duoc ngay tu tuan 1 nho cac endpoint nay.
Chu so huu: A = Hien, B = Khanh, C = Duong (xem docs/PHAN_CONG.md).
"""
from fastapi import APIRouter, Depends

from app.security import get_current_user, require_role

router = APIRouter(prefix="/api", tags=["mock-contract"], dependencies=[Depends(get_current_user)])

SAMPLE_INVOICE = {
    "invoice_id": 1, "file_type": "pdf", "invoice_series": "C26TAA", "invoice_number": "0000123",
    "invoice_date": "2026-01-15", "seller_name": "CONG TY TNHH MAU", "mst_seller": "0100000000",
    "total_before_tax": "1000000.00", "vat_rate": "10.00", "vat_amount": "100000.00",
    "total_amount": "1100000.00", "status": "cho_xac_nhan", "export_status": "chua_xuat",
}
SAMPLE_FIELDS = [
    {"field_id": 1, "field_name": "invoice_number", "extracted_value": "0000123", "final_value": None, "confidence_score": 96},
    {"field_id": 2, "field_name": "mst_seller", "extracted_value": "0100000000", "final_value": None, "confidence_score": 78},
    {"field_id": 3, "field_name": "total_amount", "extracted_value": "1100000", "final_value": None, "confidence_score": 55},
]


def mock(data, **extra):
    return {"mock": True, "data": data, **extra}


# ---- Goi A (Hien): da lam that o routers/invoices.py ----


# ---- Goi B (Khanh) ----
@router.post("/invoices/{invoice_id}/suggest-entries", tags=["B"])
def suggest_entries(invoice_id: int):
    return mock([{"debit_account": "642", "credit_account": "331", "amount": "1000000.00",
                  "source": "ml", "probability": 0.82}])


@router.put("/invoices/{invoice_id}/journal-entries", tags=["B"])
def put_entries(invoice_id: int):
    return mock({"saved": True})


# ---- Goi C (Duong) ----
@router.post("/invoices/{invoice_id}/submit", tags=["C"])
def submit(invoice_id: int):
    return mock({"status": "cho_duyet"})


@router.post("/invoices/{invoice_id}/approve", tags=["C"], dependencies=[Depends(require_role("KTT"))])
def approve(invoice_id: int):
    return mock({"status": "da_duyet"})


@router.post("/invoices/{invoice_id}/reject", tags=["C"], dependencies=[Depends(require_role("KTT"))])
def reject(invoice_id: int):
    return mock({"status": "tu_choi"})


@router.get("/approvals", tags=["C"])
def approvals():
    return mock([{**SAMPLE_INVOICE, "status": "cho_duyet", "anomaly_score": 0.12}])


@router.post("/exports/sheet", tags=["C"])
def export_sheet():
    return mock({"exported": 1, "export_status": "da_xuat"})


@router.get("/purchase-orders", tags=["C"])
def list_pos():
    return mock([{"po_id": 1, "po_number": "PO-001", "vendor": "CONG TY TNHH MAU",
                  "expected_amount": "1100000.00", "status": "open"}])


@router.post("/purchase-orders", tags=["C"])
def create_po():
    return mock({"po_id": 2})


@router.post("/invoices/{invoice_id}/match-po", tags=["C"])
def match_po(invoice_id: int):
    return mock({"po_id": 1, "amount_difference": "0.00", "match_status": "khop"})


@router.get("/reports/spending", tags=["C"])
def spending():
    return mock({"by_month": [{"month": "2026-01", "total": "1100000.00"}]})
