from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import approval_po, auth, b_catalog, b_entries, b_fields, health, invoices, mock_contract
from app.services.invoice_data import recover_stuck_in_thread


@asynccontextmanager
async def lifespan(_: FastAPI):
    recover_stuck_in_thread()  # hoa don dang do vi backend vua tat/reload thi xu ly lai, khong de ket 'dang xu ly'
    yield


app = FastAPI(title="AI Invoice Accounting - Backend", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"], allow_headers=["*"],
)
settings.upload_dir.mkdir(parents=True, exist_ok=True)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(invoices.router)
app.include_router(b_fields.router)
app.include_router(b_entries.router)
app.include_router(b_catalog.router)
app.include_router(approval_po.router)
app.include_router(mock_contract.router)
