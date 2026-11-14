"""Hop dong API AI service (mock-first). Tra du lieu mau + "mock": true.
Lam xong that thi chuyen sang router rieng va XOA khoi file nay (mock dang ky truoc se de len endpoint that).
Da lam that: /ocr /extract /normalize-vendor (invoice_ai), /classify-gl /classify-doc (gl_ai),
/anomaly-score (anomaly), /match-po (po_matching). Con mock: /summarize (C8, Could).
Chu so huu: A=Hien, B=Khanh, C=Duong."""
from fastapi import APIRouter

router = APIRouter()


def mock(data):
    return {"mock": True, "data": data}


@router.post("/summarize", tags=["C"])          # C8 (Could)
def summarize():
    return mock({"summary": "Chi tieu thang 1 tang 5% so voi thang truoc."})
