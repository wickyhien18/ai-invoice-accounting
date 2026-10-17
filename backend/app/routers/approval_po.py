from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Gói C - Duyệt & PO"])

# ---------------------------------------------------------
# Nhiệm vụ C3: Luồng trạng thái hóa đơn & Hàng chờ duyệt
# ---------------------------------------------------------
@router.get("/approvals")
async def get_approvals():
    return {
        "mock": True,
        "data": [
            {"id": 1, "invoice_number": "HD-001", "vendor": "Công ty TNHH A", "total": 15000000, "status": "pending_approval"},
            {"id": 2, "invoice_number": "HD-002", "vendor": "Công ty CP B", "total": 500000, "status": "pending_approval"}
        ]
    }

@router.post("/invoices/{id}/submit")
async def submit_invoice(id: int):
    return {"mock": True, "message": f"Hóa đơn {id} đã được gửi kế toán trưởng duyệt.", "status": "pending_approval"}

@router.post("/invoices/{id}/approve")
async def approve_invoice(id: int):
    return {"mock": True, "message": f"Hóa đơn {id} đã được phê duyệt.", "status": "approved", "approved_by": "ktt@demo.local"}

@router.post("/invoices/{id}/reject")
async def reject_invoice(id: int, reason: str = "Sai thông tin đối chiếu"):
    return {"mock": True, "message": f"Hóa đơn {id} bị từ chối.", "status": "rejected", "reject_reason": reason}

# ---------------------------------------------------------
# Nhiệm vụ C4: Xuất bảng kê
# ---------------------------------------------------------
@router.post("/exports/sheet")
async def export_sheet():
    return {
        "mock": True, 
        "message": "Đã xuất bảng kê 01-2/GTGT.", 
        "download_url": "http://localhost:8000/static/mock_export_01_2.xlsx"
    }

# ---------------------------------------------------------
# Nhiệm vụ C6: Nhập và Quản lý PO
# ---------------------------------------------------------
@router.get("/purchase-orders")
async def get_purchase_orders():
    return {
        "mock": True,
        "data": [
            {"id": 1, "po_number": "PO-2026-001", "vendor": "Công ty TNHH A", "total_amount": 15000000},
            {"id": 2, "po_number": "PO-2026-002", "vendor": "Công ty CP C", "total_amount": 32000000}
        ]
    }

@router.post("/purchase-orders")
async def create_purchase_order():
    return {"mock": True, "message": "Đã tạo Đơn mua hàng (PO) mới thành công."}

# ---------------------------------------------------------
# Nhiệm vụ C7: Đối chiếu PO
# ---------------------------------------------------------
@router.post("/invoices/{id}/match-po")
async def match_po_with_invoice(id: int):
    return {
        "mock": True, 
        "message": "Đối chiếu thành công.",
        "match_status": "matched", 
        "amount_difference": 0, 
        "matched_po": "PO-2026-001"
    }