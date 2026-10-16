from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv(Path(__file__).resolve().parents[2] / ".env")  # .env DUY NHAT o thu muc goc

from app.routers import mock_contract  # noqa: E402

app = FastAPI(title="AI Invoice Accounting - AI Service")
app.include_router(mock_contract.router)


@app.get("/health")
def health():
    return {"status": "ok"}
