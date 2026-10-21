from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from sentence_transformers import SentenceTransformer, util

router = APIRouter(tags=["AI PO Matching"])

# Khởi tạo mô hình bge-m3 (Lazy loading)
_bge_m3_model = None

def get_model():
    global _bge_m3_model
    if _bge_m3_model is None:
        # BAAI/bge-m3 hỗ trợ đa ngôn ngữ và xử lý tiếng Việt rất tốt
        _bge_m3_model = SentenceTransformer("BAAI/bge-m3")
    return _bge_m3_model


class CandidatePO(BaseModel):
    po_id: int
    po_number: str
    vendor: str


class POMatchRequest(BaseModel):
    seller_name: str
    candidates: List[CandidatePO]


class POMatchResponse(BaseModel):
    best_po_id: Optional[int] = None
    best_po_number: Optional[str] = None
    similarity_score: float = 0.0


@router.post("/match-po", response_model=POMatchResponse)
def match_po_with_bge_m3(payload: POMatchRequest):
    if not payload.candidates or not payload.seller_name.strip():
        return POMatchResponse()

    model = get_model()

    query_text = payload.seller_name.strip()
    candidate_texts = [c.vendor.strip() for c in payload.candidates]

    # Chuyển đổi văn bản sang vector nhúng
    query_emb = model.encode(query_text, convert_to_tensor=True)
    candidate_embs = model.encode(candidate_texts, convert_to_tensor=True)

    # Tính điểm tương đồng Cosine
    cosine_scores = util.cos_sim(query_emb, candidate_embs)[0]

    # Tìm ứng viên có độ tương đồng cao nhất
    best_idx = int(cosine_scores.argmax())
    best_score = float(cosine_scores[best_idx])

    # Ngưỡng tin cậy (>= 0.55 được coi là khớp về tên nhà cung cấp)
    if best_score >= 0.55:
        best_cand = payload.candidates[best_idx]
        return POMatchResponse(
            best_po_id=best_cand.po_id,
            best_po_number=best_cand.po_number,
            similarity_score=round(best_score, 4),
        )

    return POMatchResponse(similarity_score=round(best_score, 4))