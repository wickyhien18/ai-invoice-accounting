from app.database import SessionLocal
from app.models.invoice import Invoice
from decimal import Decimal

db = SessionLocal()

# Tạo một hóa đơn đang ở trạng thái chờ duyệt
test_invoice = Invoice(
    uploaded_by=1, # Giả định user ID 1 có tồn tại (từ seed_demo)
    file_path="mock/path.pdf",
    file_type="pdf",
    invoice_number="HD-DEMO-001",
    seller_name="Công ty TNHH AI Demo",
    total_amount=Decimal("15500000"),
    status="cho_duyet", # Trạng thái quan trọng để hiển thị lên bảng
    export_status="chua_xuat"
)

db.add(test_invoice)
db.commit()
print("Đã thêm hóa đơn test thành công!")