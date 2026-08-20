# AI Invoice Accounting

Hệ thống hỗ trợ nhập liệu hóa đơn/chứng từ kế toán bằng AI — đồ án tốt nghiệp.

## Mục tiêu

Tự động hóa việc đọc, trích xuất, đối chiếu và gán bút toán (ghi sổ kế toán)
cho hóa đơn, giảm thời gian nhập liệu thủ công và sai sót cho kế toán viên.

## 7 chức năng cốt lõi

1. Thu nhận & số hóa hóa đơn (OCR)
2. Trích xuất dữ liệu có cấu trúc (nhà cung cấp, ngày, số tiền, MST...)
3. Chuẩn hóa ngữ cảnh (NLP) — hiểu các cách viết khác nhau giữa nhà cung cấp
4. Đánh giá độ tin cậy dữ liệu trích xuất (confidence score)
5. Đối chiếu chứng từ (2-way/3-way matching)
6. Gán bút toán (GL Coding) — đề xuất Nợ/Có theo TT133/2016/TT-BTC
7. Báo cáo & phân tích xu hướng chi tiêu

## Cấu trúc thư mục

```
ai-invoice-accounting/
├── ai-service/     # Service Python xử lý OCR + LLM parse dữ liệu
├── backend/        # API chính: business logic, database, workflow duyệt
├── frontend/       # Giao diện web: upload, xác nhận, dashboard
├── database/        # Schema, migration, seed data (Chart of Accounts theo TT133)
└── docs/            # Tài liệu đồ án theo từng chương
```

## Công nghệ

| Thành phần | Công nghệ                                                      |
| ---------- | -------------------------------------------------------------- |
| AI Service | Python + FastAPI, Google Cloud Vision API / Tesseract, LLM API |
| Backend    | Python + FastAPI, SQLAlchemy, Alembic                          |
| Frontend   | React + Vite + Tailwind CSS                                    |
| Database   | MySQL 8.0 (chạy qua Docker)                                    |

Xem hướng dẫn cài đặt chi tiết tại [`SETUP.md`](./SETUP.md) — đặc biệt lưu ý
phần cấu hình MySQL để tránh lỗi charset/kết nối khi cả nhóm cùng làm việc.

## Hướng dẫn Setup

### Bước 0: Cài Docker (nếu máy chưa có)

Dự án dùng Docker để chạy MySQL — đảm bảo cả 3 thành viên chạy cùng 1 phiên
bản MySQL giống hệt nhau, tránh lỗi lệch cấu hình giữa các máy.

- **Windows/Mac:** tải Docker Desktop tại https://www.docker.com/products/docker-desktop
  → cài như phần mềm bình thường → mở lên, đợi biểu tượng cá voi hết trạng
  thái loading (nghĩa là Docker đã sẵn sàng)
- **Linux:** cài Docker Engine theo hướng dẫn tại
  https://docs.docker.com/engine/install/

Kiểm tra đã cài thành công:

```bash
docker --version
docker compose version
```

### Bước 1: Tạo file `.env` và chạy MySQL

```bash
cp .env.example .env    # điền/giữ giá trị mặc định cho MySQL
docker compose up -d mysql
```

Lần đầu chạy sẽ mất vài phút để tải image MySQL 8.0.

Kiểm tra MySQL đã sẵn sàng:

```bash
docker compose ps        # trạng thái phải là "healthy"
docker compose logs mysql
```

### Bước 2: Chạy AI Service

```bash
cd ai-service
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # điền API key OCR/LLM
uvicorn app.main:app --reload --port 8001
```

### Bước 3: Chạy Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env           # điền thông tin kết nối MySQL
uvicorn app.main:app --reload --port 8000
```

### Bước 4: Chạy Frontend

```bash
cd frontend
npm install
npm run dev
```

### Thứ tự chạy mỗi khi bắt đầu code

```bash
docker compose up -d mysql
# sau đó mở 3 terminal riêng cho backend, ai-service, frontend
```

Xem thêm chi tiết nguyên tắc giữ MySQL ổn định (charset, kiểu dữ liệu tiền,
connection pool, migration) tại [`SETUP.md`](./SETUP.md).
