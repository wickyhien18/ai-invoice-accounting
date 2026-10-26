"""Goi A o ai-service: POST /ocr (A6), POST /extract (A7), POST /normalize-vendor (A8). Endpoint THAT.

Tra ve {"data": ...} (giu dang hop dong mock, bo co "mock").
"""
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app import progress
from app.services import extractor, ocr, vendor

router = APIRouter()
MAX_BYTES = 10 * 1024 * 1024


def _read(file: UploadFile) -> bytes:
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File lon hon 10 MB")
    if not data:
        raise HTTPException(422, "File rong")
    return data


def _run_ocr(file: UploadFile, force_ocr: bool, preprocess: bool) -> dict:
    data = _read(file)
    try:
        return ocr.run_ocr(data, file.filename or "", force_ocr=force_ocr, do_preprocess=preprocess)
    except ocr.UnsupportedFile as e:
        raise HTTPException(415, str(e))
    except ocr.OCRUnavailable as e:
        raise HTTPException(503, str(e))


@router.post("/ocr", tags=["A"])
def ocr_endpoint(file: UploadFile = File(...), force_ocr: bool = Form(False), preprocess: bool = Form(True)):
    """PDF co lop chu doc thang; anh/PDF scan chay PaddleOCR. force_ocr=true ep PDF di qua OCR (de do dac)."""
    return {"data": _run_ocr(file, force_ocr, preprocess)}


@router.post("/extract", tags=["A"])
def extract_endpoint(file: UploadFile | None = File(None), text: str | None = Form(None),
                     use_llm: bool = Form(True), force_ocr: bool = Form(False), preprocess: bool = Form(True),
                     job_id: str | None = Form(None, max_length=100)):
    """Nhan file (PDF/anh) HOAC text da OCR. Tra cac truong trong yeu + do tin cay 0-100.
    job_id (tuy chon): de hoi tien do qua GET /progress/{job_id}."""
    if file is None and not text:
        raise HTTPException(422, "Can gui file hoac text")
    reading = lambda: progress.set_progress(job_id, 15, "Đang đọc chữ trên tài liệu")  # noqa: E731
    if ocr.is_busy():  # ai-service doc anh lan luot: bao ro dang xep hang thay vi dung im o 15%
        progress.set_progress(job_id, 5, "Đang chờ tới lượt (hóa đơn khác đang được đọc)")
    else:
        reading()
    if file is not None:
        token = ocr.ON_START.set(reading)  # toi luot that thi chuyen sang 'Dang doc chu'
        try:
            o = _run_ocr(file, force_ocr, preprocess)
        finally:
            ocr.ON_START.reset(token)
    else:
        o = {"text": text, "lines": None, "avg_confidence": None, "source": "text"}
    progress.set_progress(job_id, 55, "Đang trích xuất các trường bằng AI")
    result = extractor.extract_fields(o, use_llm=use_llm)
    progress.set_progress(job_id, 95, "Đang lưu kết quả")
    return {"data": result}


@router.get("/progress/{job_id}", tags=["A"])
def progress_endpoint(job_id: str):
    """Buoc xu ly hien tai cua mot job_id: {"percent": 0-100, "stage": "..."}; chua co thi 404."""
    p = progress.get_progress(job_id)
    if p is None:
        raise HTTPException(404, "Khong co tien do cho job nay")
    return {"data": p}


class VendorIn(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    candidates: list[str] = Field(default_factory=list, max_length=5000)


@router.post("/normalize-vendor", tags=["A"])
def normalize_vendor_endpoint(body: VendorIn):
    return {"data": vendor.normalize_vendor(body.name, body.candidates)}
