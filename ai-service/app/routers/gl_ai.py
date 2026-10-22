"""Goi B o ai-service: POST /classify-gl (B5, co Gemini du phong cho nguoi ban moi - B6), POST /classify-doc (B8).

Tra ve {"data": ...} (giu dang hop dong mock, bo co "mock").
"""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import llm
from app.services import doc_model, gl_model, masking

log = logging.getLogger(__name__)
router = APIRouter()


class Account(BaseModel):
    code: str = Field(max_length=10)
    name: str = Field(max_length=200)


class ClassifyGLIn(BaseModel):
    seller_name: str | None = Field(None, max_length=200)
    vat_rate: float | None = None
    total_before_tax: float | None = None
    # use_llm=true: nguoi ban MOI (backend khong co lich su) -> neu ML duoi nguong tin cay thi hoi Gemini
    use_llm: bool = False
    # danh muc tai khoan hien co trong CSDL: Gemini chi duoc chon trong danh sach nay
    accounts: list[Account] | None = Field(None, max_length=300)


def _ask_llm(body: ClassifyGLIn, ml: dict) -> dict | None:
    """Hoi Gemini qua llm.py dung chung. Loi/khong hop le -> None (de dung ket qua ML)."""
    accounts = body.accounts or []
    allowed = {a.code for a in accounts}
    lines = "\n".join(f"{a.code}: {a.name}" for a in accounts)
    name = masking.mask(body.seller_name or "")[0] if masking.enabled() else (body.seller_name or "")
    prompt = (
        "Ban la ke toan Viet Nam, ap dung Thong tu 133/2016/TT-BTC. Hay goi y dinh khoan cho dong hang chinh "
        "(chua tinh thue GTGT) cua mot hoa don mua vao.\n"
        f"Nguoi ban: {name}\nThue suat GTGT: {body.vat_rate}%\nTien truoc thue: {body.total_before_tax} VND\n"
        f"Mo hinh thong ke goi y: No {ml['debit_account']}, Co {ml['credit_account']} (do tin cay thap, hay tu danh gia).\n"
        "Chi duoc chon tai khoan trong danh sach sau:\n" + lines
    )
    schema = {"debit_account": "ma tai khoan No", "credit_account": "ma tai khoan Co",
              "reason": "mot cau ngan giai thich"}
    try:
        out = llm.generate_json(prompt, schema)
    except (llm.LLMUnavailable, llm.LLMError) as e:
        log.warning("classify-gl: Gemini khong dung duoc: %s", e)
        return {"error": str(e)}
    d, c = str(out.get("debit_account", "")).strip(), str(out.get("credit_account", "")).strip()
    if allowed and (d not in allowed or c not in allowed):
        return {"error": f"Gemini trả tài khoản ngoài danh mục: {d}/{c}"}
    if not d or not c or d == c:
        return {"error": "Gemini trả tài khoản không hợp lệ"}
    return {"debit_account": d, "credit_account": c, "reason": str(out.get("reason", ""))[:300]}


@router.post("/classify-gl", tags=["B"])
def classify_gl(body: ClassifyGLIn):
    try:
        ml = gl_model.predict(body.seller_name, body.vat_rate, body.total_before_tax)
    except gl_model.ModelUnavailable as e:
        raise HTTPException(503, str(e))
    ml["source"] = "ml"
    if body.use_llm and body.accounts and ml["probability"] < gl_model.CONFIDENT:
        g = _ask_llm(body, ml)
        if g and "error" not in g:
            return {"data": {**ml, "debit_account": g["debit_account"], "credit_account": g["credit_account"],
                             "source": "llm", "probability": None, "reason": g["reason"], "ml_suggestion": {
                                 "debit_account": ml["debit_account"], "credit_account": ml["credit_account"],
                                 "probability": ml["probability"]}}}
        if g:
            ml["llm_error"] = g["error"]
    return {"data": ml}


class ClassifyDocIn(BaseModel):
    text: str = Field(max_length=100_000)


@router.post("/classify-doc", tags=["B"])
def classify_doc(body: ClassifyDocIn):
    if not body.text.strip():
        raise HTTPException(422, "Văn bản rỗng")
    try:
        return {"data": doc_model.predict(body.text)}
    except gl_model.ModelUnavailable as e:
        raise HTTPException(503, str(e))
