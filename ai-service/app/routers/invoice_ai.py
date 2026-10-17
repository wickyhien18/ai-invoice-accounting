"""Goi A o ai-service: POST /ocr (A6), POST /extract (A7), POST /normalize-vendor (A8). Endpoint THAT.

Tra ve {"data": ...} (giu dang hop dong mock, bo co "mock").
"""
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

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
                     use_llm: bool = Form(True), force_ocr: bool = Form(False), preprocess: bool = Form(True)):
    """Nhan file (PDF/anh) HOAC text da OCR. Tra cac truong trong yeu + do tin cay 0-100."""
    if file is None and not text:
        raise HTTPException(422, "Can gui file hoac text")
    if file is not None:
        o = _run_ocr(file, force_ocr, preprocess)
    else:
        o = {"text": text, "lines": None, "avg_confidence": None, "source": "text"}
    return {"data": extractor.extract_fields(o, use_llm=use_llm)}


class VendorIn(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    candidates: list[str] = Field(default_factory=list, max_length=5000)


@router.post("/normalize-vendor", tags=["A"])
def normalize_vendor_endpoint(body: VendorIn):
    return {"data": vendor.normalize_vendor(body.name, body.candidates)}
