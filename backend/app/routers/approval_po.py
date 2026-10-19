from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models.invoice import Invoice
from app.security import get_current_user, require_role

from pydantic import BaseModel
from datetime import date
from decimal import Decimal
from app.models.purchase_order import PurchaseOrder

import os
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from fastapi.responses import FileResponse

# Tạo Schema để kiểm tra dữ liệu từ Frontend gửi lên
class POCreate(BaseModel):
    po_number: str
    vendor: str
    order_date: date
    expected_amount: Decimal

router = APIRouter(prefix="/api", tags=["Gói C - Duyệt & PO"])

# ---------------------------------------------------------
# Nhiệm vụ C3: Luồng trạng thái hóa đơn & Hàng chờ duyệt
# ---------------------------------------------------------
@router.get("/approvals")
async def get_approvals(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Lấy các hóa đơn đang chờ kế toán trưởng duyệt
    invoices = db.query(Invoice).filter(Invoice.status == "cho_duyet").all()
    return {"data": invoices}

@router.post("/invoices/{invoice_id}/submit")
async def submit_invoice(invoice_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Không tìm thấy hóa đơn")
    
    invoice.status = "cho_duyet"
    db.commit()
    return {"message": f"Hóa đơn {invoice_id} đã được gửi kế toán trưởng duyệt.", "status": "cho_duyet"}

@router.post("/invoices/{invoice_id}/approve")
async def approve_invoice(invoice_id: int, db: Session = Depends(get_db), current_user = Depends(require_role("KTT"))):
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Không tìm thấy hóa đơn")
    
    invoice.status = "da_duyet"
    invoice.approved_by = current_user.user_id 
    invoice.approved_at = datetime.now()
    db.commit()
    return {"message": f"Hóa đơn {invoice_id} đã được phê duyệt.", "status": "da_duyet", "approved_by": current_user.email}

@router.post("/invoices/{invoice_id}/reject")
async def reject_invoice(invoice_id: int, reason: str, db: Session = Depends(get_db), current_user = Depends(require_role("KTT"))):
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Không tìm thấy hóa đơn")
    
    if not reason:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp lý do từ chối")
        
    invoice.status = "tu_choi"
    invoice.reject_reason = reason
    db.commit()
    return {"message": f"Hóa đơn {invoice_id} bị từ chối.", "status": "tu_choi", "reject_reason": reason}

# ---------------------------------------------------------
# Nhiệm vụ C4: Xuất bảng kê (Đã làm đẹp định dạng Excel)
# ---------------------------------------------------------
@router.post("/exports/sheet")
async def export_sheet(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # 1. Tìm các hóa đơn ĐÃ DUYỆT nhưng CHƯA XUẤT
    invoices = db.query(Invoice).filter(
        Invoice.status == "da_duyet", 
        Invoice.export_status == "chua_xuat"
    ).all()
    
    if not invoices:
        raise HTTPException(status_code=400, detail="Không có hóa đơn nào ở trạng thái 'Đã duyệt' và 'Chưa xuất'.")
    
    # 2. Tạo file Excel mới với openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bảng kê 01-2 GTGT"
    
    # Gộp ô và viết tiêu đề chính
    ws.merge_cells('A1:I1')
    title_cell = ws['A1']
    title_cell.value = "BẢNG KÊ HÓA ĐƠN, CHỨNG TỪ HÀNG HÓA, DỊCH VỤ MUA VÀO (Mẫu 01-2/GTGT)"
    title_cell.font = Font(bold=True, size=14, color="003366")
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Bỏ trống dòng 2
    ws.append([]) 
    
    # Header các cột
    headers = [
        "STT", "Ký hiệu hóa đơn", "Số hóa đơn", "Ngày lập", 
        "Tên người bán", "MST người bán", "Doanh số mua chưa thuế", 
        "Thuế GTGT", "Ghi chú"
    ]
    ws.append(headers)
    
    # Set độ rộng cột
    column_widths = {'A': 5, 'B': 18, 'C': 18, 'D': 15, 'E': 45, 'F': 18, 'G': 22, 'H': 22, 'I': 20}
    for col_letter, width in column_widths.items():
        ws.column_dimensions[col_letter].width = width
    
    # Căn lề, tạo viền và đổ màu nền cho header (Dòng 3)
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="0070C0", end_color="0070C0", fill_type="solid")
    border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                    top=Side(style='thin'), bottom=Side(style='thin'))
    
    for cell in ws[3]:
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    total_revenue = 0.0
    total_tax = 0.0
    
    # 3. Ghi dữ liệu hóa đơn vào bảng
    for idx, inv in enumerate(invoices, 1):
        revenue = float(inv.total_before_tax or 0)
        tax = float(inv.vat_amount or 0)
        
        row = [
            idx,
            inv.invoice_series or "",
            inv.invoice_number or "",
            inv.invoice_date.strftime("%d/%m/%Y") if inv.invoice_date else "",
            inv.seller_name or "",
            inv.mst_seller or "",
            revenue,
            tax,
            ""
        ]
        ws.append(row)
        total_revenue += revenue
        total_tax += tax
        
        # Cập nhật trạng thái hóa đơn để chống xuất lặp
        inv.export_status = "da_xuat"
        inv.exported_at = datetime.now()
        
        # Kẻ viền và định dạng dữ liệu cho dòng hiện tại
        current_row = ws[ws.max_row]
        for cell in current_row:
            cell.border = border
            
        # Căn giữa STT, Ngày, MST
        current_row[0].alignment = Alignment(horizontal='center')
        current_row[3].alignment = Alignment(horizontal='center')
        current_row[5].alignment = Alignment(horizontal='center')
        
        # Định dạng số tiền có dấu phẩy phân cách hàng nghìn
        current_row[6].number_format = '#,##0'
        current_row[7].number_format = '#,##0'
            
    # 4. Ghi dòng Tổng cộng
    ws.append(["", "", "", "", "TỔNG CỘNG:", "", total_revenue, total_tax, ""])
    summary_row = ws[ws.max_row]
    
    for cell in summary_row:
        cell.font = Font(bold=True, color="9C0006")
        cell.border = border
    
    summary_row[4].alignment = Alignment(horizontal='right')
    summary_row[6].number_format = '#,##0'
    summary_row[7].number_format = '#,##0'
        
    db.commit()
    
    # 5. Lưu file vào ổ cứng
    export_dir = "storage/exports"
    os.makedirs(export_dir, exist_ok=True)
    filename = f"Bang_ke_01_2_GTGT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(export_dir, filename)
    wb.save(filepath)
    
    # Trả về URL để React tải file
    return {
        "message": f"Đã xuất thành công bảng kê cho {len(invoices)} hóa đơn.", 
        "download_url": f"/api/exports/download/{filename}"
    }

# Endpoint phụ trợ dùng để thực sự tải file Excel từ Frontend
@router.get("/exports/download/{filename}")
async def download_export(filename: str):
    filepath = os.path.join("storage/exports", filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File không tồn tại.")
    return FileResponse(
        filepath, 
        filename=filename, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ---------------------------------------------------------
# Nhiệm vụ C6: Nhập và Quản lý PO
# ---------------------------------------------------------
@router.get("/purchase-orders")
async def get_purchase_orders(db: Session = Depends(get_db)):
    # Lấy toàn bộ danh sách PO từ database, sắp xếp mới nhất lên đầu
    pos = db.query(PurchaseOrder).order_by(PurchaseOrder.po_id.desc()).all()
    return {"data": pos}

@router.post("/purchase-orders")
async def create_purchase_order(
    po_data: POCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Kiểm tra xem mã PO này đã tồn tại trong hệ thống chưa
    existing_po = db.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_data.po_number).first()
    if existing_po:
        raise HTTPException(status_code=400, detail="Mã đơn mua hàng (PO) đã tồn tại.")

    # Tạo bản ghi PO mới theo model
    new_po = PurchaseOrder(
        po_number=po_data.po_number,
        vendor=po_data.vendor,
        order_date=po_data.order_date,
        expected_amount=po_data.expected_amount,
        status="dang_mo",  # Trạng thái mặc định khi vừa tạo
        created_by=current_user.user_id
    )
    
    db.add(new_po)
    db.commit()
    db.refresh(new_po)
    
    return {
        "message": "Đã tạo Đơn mua hàng (PO) mới thành công.", 
        "data": new_po
    }

# ---------------------------------------------------------
# Nhiệm vụ C7: Đối chiếu PO
# ---------------------------------------------------------
@router.post("/invoices/{invoice_id}/match-po")
async def match_po_with_invoice(invoice_id: int):
    return {
        "mock": True, 
        "message": "Đối chiếu thành công.",
        "match_status": "matched", 
        "amount_difference": 0, 
        "matched_po": "PO-2026-001"
    }