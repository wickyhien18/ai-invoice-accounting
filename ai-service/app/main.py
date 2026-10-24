import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.routers import gl_ai, invoice_ai, mock_contract, po_matching, anomaly  # <--- Bổ sung po_matching và anomaly
from app.services import ocr


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("OCR_WARMUP", "1") != "0":
        threading.Thread(target=ocr.warmup, daemon=True).start()
    yield


app = FastAPI(title="AI Invoice Accounting - AI Service", lifespan=lifespan)
app.include_router(invoice_ai.router)
app.include_router(gl_ai.router)
app.include_router(mock_contract.router)
app.include_router(po_matching.router)  # <--- Đăng ký router đối chiếu PO
app.include_router(anomaly.router)

@app.get("/health")
def health():
    return {"status": "ok", "ocr_ready": ocr.is_ready()}