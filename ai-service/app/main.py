import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv(Path(__file__).resolve().parents[2] / ".env")  # .env DUY NHAT o thu muc goc

from app.routers import invoice_ai, mock_contract  # noqa: E402
from app.services import ocr  # noqa: E402


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Nap PaddleOCR o luong rieng de dich vu len ngay; dat OCR_WARMUP=0 de tat
    if os.getenv("OCR_WARMUP", "1") != "0":
        threading.Thread(target=ocr.warmup, daemon=True).start()
    yield


app = FastAPI(title="AI Invoice Accounting - AI Service", lifespan=lifespan)
app.include_router(invoice_ai.router)
app.include_router(mock_contract.router)


@app.get("/health")
def health():
    return {"status": "ok", "ocr_ready": ocr.is_ready()}
