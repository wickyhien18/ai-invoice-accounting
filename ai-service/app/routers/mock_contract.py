"""Hop dong API AI service (mock-first). Tra du lieu mau + "mock": true.
Lam xong that thi chuyen sang router rieng va xoa khoi file nay. Chu so huu: A=Hien, B=Khanh, C=Duong."""
from fastapi import APIRouter

router = APIRouter()


def mock(data):
    return {"mock": True, "data": data}


@router.post("/ocr", tags=["A"])        # A6
def ocr():
    return mock({"text": "HOA DON GIA TRI GIA TANG ...", "lines": []})


@router.post("/extract", tags=["A"])    # A7
def extract():
    return mock({"fields": {"invoice_number": {"value": "0000123", "confidence": 96},
                            "mst_seller": {"value": "0100000000", "confidence": 78},
                            "total_amount": {"value": "1100000", "confidence": 55}}})


@router.post("/normalize-vendor", tags=["A"])   # A8
def normalize_vendor():
    return mock({"canonical": "CONG TY TNHH MAU", "score": 97})


@router.post("/classify-gl", tags=["B"])        # B5
def classify_gl():
    return mock({"debit_account": "642", "credit_account": "331", "probability": 0.82})


@router.post("/classify-doc", tags=["B"])       # B8 (Could)
def classify_doc():
    return mock({"doc_type": "hoa_don_gtgt", "probability": 0.9})


@router.post("/anomaly-score", tags=["C"])      # C5
def anomaly_score():
    return mock({"score": 0.12, "is_anomaly": False, "is_duplicate": False})


@router.post("/match-po", tags=["C"])           # C7
def match_po():
    return mock({"po_id": 1, "similarity": 0.91})


@router.post("/summarize", tags=["C"])          # C8 (Could)
def summarize():
    return mock({"summary": "Chi tieu thang 1 tang 5% so voi thang truoc."})
