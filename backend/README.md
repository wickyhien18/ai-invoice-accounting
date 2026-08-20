# Backend

Chịu trách nhiệm:
- API chính cho frontend
- Database (hóa đơn, chứng từ, chart of accounts, bút toán, người dùng)
- Business logic: đối chiếu chứng từ, gán bút toán, workflow duyệt
- Xác thực & phân quyền (JWT)
- Gọi sang `ai-service` để lấy kết quả OCR + trích xuất

## Công nghệ
Python + FastAPI, SQLAlchemy (ORM), Alembic (migration), MySQL, JWT (auth)

## Các bảng chính cần thiết kế
- `users` — kế toán viên / kế toán trưởng
- `invoices` — hóa đơn gốc, trạng thái xử lý
- `invoice_fields` — dữ liệu trích xuất kèm confidence_score
- `chart_of_accounts` — danh mục tài khoản theo Phụ lục 1, TT133/2016/TT-BTC
- `journal_entries` — bút toán (Nợ/Có)
- `matching_results` — kết quả đối chiếu PO – GRN – Invoice
