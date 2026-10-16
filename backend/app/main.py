from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, health, mock_contract

app = FastAPI(title="AI Invoice Accounting - Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"], allow_headers=["*"],
)
settings.upload_dir.mkdir(parents=True, exist_ok=True)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(mock_contract.router)
