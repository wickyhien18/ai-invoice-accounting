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
@router.get("/invoices/{invoice_id}/fields", tags=["B"])
def get_fields(invoice_id: int):
    return mock(SAMPLE_FIELDS)


@router.patch("/invoices/{invoice_id}/fields/{field_id}", tags=["B"])
def patch_field(invoice_id: int, field_id: int):
    return mock({**SAMPLE_FIELDS[0], "field_id": field_id})


@router.post("/invoices/{invoice_id}/suggest-entries", tags=["B"])
def suggest_entries(invoice_id: int):
    return mock([{"debit_account": "642", "credit_account": "331", "amount": "1000000.00",
                  "source": "ml", "probability": 0.82}])


@router.put("/invoices/{invoice_id}/journal-entries", tags=["B"])
def put_entries(invoice_id: int):
    return mock({"saved": True})


# ---- Goi C (Duong) ----
