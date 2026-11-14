"""HOP DONG API (mock-first). Endpoint nao chua lam that thi tra du lieu mau + "mock": true.

Quy tac nhom: khi lam xong that mot endpoint thi XOA no khoi file nay (router that nam o file rieng).
Mock dang ky SAU cac router that nen khong de len duoc, nhung de lai thi test va tai lieu bi sai.
Da lam that het cac goi A, B, C; chi con /reports/spending (C8, Could) la mock.
"""
from fastapi import APIRouter, Depends

from app.security import get_current_user

router = APIRouter(prefix="/api", tags=["mock-contract"], dependencies=[Depends(get_current_user)])


@router.get("/reports/spending", tags=["C"])
def spending():
    return {"mock": True, "data": {"by_month": [{"month": "2026-01", "total": "1100000.00"}]}}
