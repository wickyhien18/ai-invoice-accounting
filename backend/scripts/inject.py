# Đây là một script Python để bơm dữ liệu hóa đơn ngẫu nhiên vào cơ sở dữ liệu. Nó tạo ra các hóa đơn với thông tin ngẫu nhiên như tên người bán, mã số thuế, số hóa đơn, ngày hóa đơn, doanh số, thuế VAT và tổng số tiền. Các hóa đơn này được đánh dấu là "cho_duyet" để sẵn sàng cho kế toán trưởng duyệt.
# Có thể xóa các hóa đơn này sau khi kiểm tra bằng cách xóa các bản ghi trong bảng `Invoice` có `status="cho_duyet"`.

import os
import sys
import random
from datetime import date, timedelta
from decimal import Decimal

# Xử lý lỗi ModuleNotFoundError bằng cách thêm thư mục gốc vào path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.invoice import Invoice

db = SessionLocal()

# Tập dữ liệu mẫu ngẫu nhiên
SELLERS = [
    ("Công ty CP Vận tải Mẫu Thử Dũng", "0487211601"),
    ("Công ty CP Thực Phẩm Mẫu Thử Lan", "0504834002"),
    ("Công ty TNHH AI Invoice Demo", "0123456789"),
    ("Công ty TNHH Thương mại Dịch vụ ABC", "0311223344"),
    ("Công ty Cổ phần Công nghệ TechZ", "0102030405")
]

SERIES_LIST = ["C26TAA", "C26MBF", "C26TRU", "K26TBB"]

def inject_random_invoices(num_invoices=5):
    print(f"Đang tạo {num_invoices} hóa đơn ngẫu nhiên...")
    
    for _ in range(num_invoices):
        seller_name, mst = random.choice(SELLERS)
        invoice_series = random.choice(SERIES_LIST)
        invoice_number = f"{random.randint(1, 9999999):07d}"
        
        # Ngày ngẫu nhiên trong vòng 30 ngày qua
        random_days_ago = random.randint(0, 30)
        inv_date = date.today() - timedelta(days=random_days_ago)
        
        # Doanh số ngẫu nhiên từ 1.000.000 đến 50.000.000 VNĐ
        revenue = random.randint(1000, 50000) * 1000
        vat_rate_choice = random.choice([8, 10])
        
        total_before_tax = Decimal(str(revenue))
        vat_rate = Decimal(str(vat_rate_choice))
        vat_amount = total_before_tax * (vat_rate / Decimal('100'))
        total_amount = total_before_tax + vat_amount
        
        new_invoice = Invoice(
            uploaded_by=1, 
            file_path=f"fake_data_{invoice_number}.pdf",
            file_type="pdf",
            invoice_series=invoice_series,
            invoice_number=invoice_number,
            invoice_date=inv_date,
            seller_name=seller_name,
            mst_seller=mst,
            total_before_tax=total_before_tax,
            vat_rate=vat_rate,
            vat_amount=vat_amount,
            total_amount=total_amount,
            status="cho_duyet",  # Sẵn sàng để KTT duyệt
            export_status="chua_xuat"
        )
        db.add(new_invoice)
        
    db.commit()
    print(f"✅ Đã bơm thành công {num_invoices} hóa đơn vào Hàng chờ duyệt!")

if __name__ == "__main__":
    # Thay đổi số 5 thành số lượng hóa đơn bạn muốn tạo mỗi lần chạy
    inject_random_invoices(10)