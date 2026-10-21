from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import numpy as np
from sklearn.ensemble import IsolationForest

router = APIRouter(tags=["AI Anomaly Detection"])

class InvoiceData(BaseModel):
    invoice_id: int
    seller_name: Optional[str] = ""
    total_amount: Optional[float] = 0.0

class AnomalyResponseItem(BaseModel):
    invoice_id: int
    is_anomaly: bool
    anomaly_score: float
    reason: str

@router.post("/anomaly-score", response_model=List[AnomalyResponseItem])
def detect_anomalies(invoices: List[InvoiceData]):
    if not invoices:
        return []
    
    results = []
    
    # 1. Phát hiện trùng lặp (Rule-based: Trùng cả tên và số tiền)
    seen = {}
    duplicate_ids = set()
    for inv in invoices:
        key = f"{inv.seller_name}_{inv.total_amount}"
        if key in seen:
            duplicate_ids.add(inv.invoice_id)
            duplicate_ids.add(seen[key])
        else:
            seen[key] = inv.invoice_id

    # 2. Phát hiện bất thường bằng Isolation Forest (Machine Learning)
    amounts = [inv.total_amount for inv in invoices]
    preds = []
    scores = []
    
    # Isolation Forest cần ít nhất 4 dữ liệu để tìm ra sự khác biệt
    if len(amounts) >= 4:
        X = np.array(amounts).reshape(-1, 1)
        # Giả định có tối đa 10% dữ liệu bị lỗi/bất thường
        clf = IsolationForest(contamination=0.1, random_state=42)
        clf.fit(X)
        preds = clf.predict(X)  # -1 là bất thường, 1 là bình thường
        scores = clf.decision_function(X) # Càng âm càng bất thường
    else:
        # Nếu ít hơn 4 hóa đơn, mặc định cho là bình thường
        preds = [1] * len(amounts)
        scores = [1.0] * len(amounts)

    # 3. Gộp kết quả
    for idx, inv in enumerate(invoices):
        is_ml_anomaly = bool(preds[idx] == -1)
        is_dup_anomaly = inv.invoice_id in duplicate_ids
        
        reason = []
        if is_dup_anomaly:
            reason.append("Trùng lặp: Phát hiện hóa đơn khác có cùng tên nhà cung cấp và số tiền.")
        if is_ml_anomaly:
            reason.append("Bất thường: Số tiền cao/thấp đột biến so với mặt bằng chung.")
            
        results.append(AnomalyResponseItem(
            invoice_id=inv.invoice_id,
            is_anomaly=(is_ml_anomaly or is_dup_anomaly),
            anomaly_score=round(float(scores[idx]), 4),
            reason=" | ".join(reason)
        ))
        
    return results