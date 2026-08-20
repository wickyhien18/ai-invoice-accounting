# Hướng dẫn Setup dự án — ai-invoice-accounting

Stack đã chốt:
- **Backend:** Python + FastAPI
- **AI Service:** Python + FastAPI
- **Frontend:** React + Tailwind CSS
- **Database:** MySQL

Tài liệu này hướng dẫn từng thành viên setup môi trường local, và cách cấu
hình MySQL để tránh các lỗi phổ biến (mất kết nối, sai charset, lệch dữ
liệu số tiền do kiểu dữ liệu sai).

---

## 0. Yêu cầu chung trước khi bắt đầu

Cài sẵn trên máy:
- Python 3.11+
- Node.js 20 LTS+
- Docker Desktop (khuyến nghị dùng Docker để chạy MySQL — tránh lỗi cài đặt
  MySQL trực tiếp trên từng máy khác nhau giữa 3 thành viên)
- Git

Kiểm tra:
```bash
python3 --version
node --version
docker --version
```

---

## 1. MySQL — cách chạy ổn định bằng Docker (khuyến nghị)

**Lý do dùng Docker thay vì cài MySQL trực tiếp:** cả 3 thành viên chạy
đúng 1 phiên bản MySQL giống hệt nhau, tránh tình trạng "chạy được trên máy
tui nhưng lỗi trên máy bạn" — nguyên nhân phổ biến nhất là do khác phiên
bản MySQL hoặc khác charset mặc định.

### 1.1. File `docker-compose.yml` (đặt ở thư mục gốc repo)

Xem file `docker-compose.yml` đã tạo sẵn trong repo. Điểm quan trọng cần
hiểu trong file đó:

- `MYSQL_CHARACTER_SET=utf8mb4` — **bắt buộc** để lưu đúng tiếng Việt có
  dấu (VD: "Công ty ABC", "Nguyễn Văn A"). Nếu dùng charset mặc định
  (`latin1`), dữ liệu tiếng Việt sẽ bị lỗi ký tự (hiển thị dấu `?` hoặc ký
  tự lạ) khi lưu vào MySQL.
- `volumes` — dữ liệu MySQL được lưu ra ngoài container, nếu container bị
  xóa/restart thì dữ liệu vẫn còn, không mất hết mỗi lần `docker compose down`.
- `healthcheck` — Docker tự kiểm tra MySQL đã sẵn sàng nhận kết nối chưa,
  tránh việc backend khởi động và kết nối trước khi MySQL kịp khởi động
  xong (lỗi rất hay gặp: "Connection refused" khi mới `docker compose up`).

### 1.2. Chạy MySQL

```bash
docker compose up -d mysql
```

Kiểm tra MySQL đã chạy:
```bash
docker compose ps
docker compose logs mysql
```

### 1.3. Kết nối thử để xác nhận

```bash
docker exec -it ai-invoice-mysql mysql -u app_user -p ai_invoice_db
# nhập password trong file .env
```

---

## 2. Các nguyên tắc để MySQL luôn ổn định trong suốt quá trình làm đồ án

Đây là phần quan trọng nhất — áp dụng ngay từ đầu, tránh việc giữa chừng
đồ án phải sửa lại toàn bộ database vì lỗi cấu hình ban đầu.

### 2.1. Luôn dùng `utf8mb4`, không dùng `utf8`

Trong MySQL, bảng mã tên là `utf8` thực ra là bản rút gọn, **không lưu
được đầy đủ một số ký tự**. Luôn khai báo:
```sql
CREATE DATABASE ai_invoice_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

### 2.2. Kiểu dữ liệu cho số tiền — không dùng FLOAT/DOUBLE

Đây là lỗi rất hay gặp ở sinh viên khi làm hệ thống kế toán: dùng `FLOAT`
để lưu số tiền sẽ gây ra **sai số làm tròn** (VD: 2 số tiền cộng lại ra
1999.9999999 thay vì 2000). Với hệ thống kế toán, số tiền **bắt buộc**
dùng kiểu `DECIMAL`:
```sql
so_tien DECIMAL(18, 2) NOT NULL
```
`DECIMAL(18,2)` nghĩa là tối đa 18 chữ số, 2 số sau dấu phẩy — đủ cho số
tiền lớn mà không bị sai số.

### 2.3. Quản lý kết nối (connection pool) ở backend FastAPI

Nếu backend mở kết nối mới cho mỗi request mà không đóng đúng cách, MySQL
sẽ báo lỗi "Too many connections" khi nhiều người dùng thử cùng lúc (kể cả
lúc demo trước hội đồng nếu 3 người cùng test). Dùng SQLAlchemy với
connection pool cấu hình sẵn (xem `backend/app/database.py` mẫu bên dưới),
tránh tự viết kết nối MySQL thủ công bằng `mysql-connector` trực tiếp
trong từng route.

### 2.4. Luôn dùng migration (Alembic), không sửa tay database

Khi cả 3 người cùng chỉnh sửa cấu trúc bảng, nếu không dùng migration,
database của mỗi người sẽ dần khác nhau và gây lỗi khó debug. Dùng
**Alembic** để mọi thay đổi cấu trúc bảng đều được ghi thành file, đồng bộ
qua Git giữa 3 người.

### 2.5. Backup trước khi thử nghiệm dữ liệu lớn

Trước khi test import nhiều hóa đơn mẫu, nên backup:
```bash
docker exec ai-invoice-mysql mysqldump -u app_user -p ai_invoice_db > backup.sql
```

---

## 3. Setup từng thành phần

### 3.1. AI Service (`ai-service/`)

```bash
cd ai-service
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # điền API key OCR/LLM vào đây
uvicorn app.main:app --reload --port 8001
```

### 3.2. Backend (`backend/`)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env           # điền thông tin kết nối MySQL vào đây
alembic upgrade head            # tạo bảng theo migration mới nhất
uvicorn app.main:app --reload --port 8000
```

### 3.3. Frontend (`frontend/`)

```bash
cd frontend
npm install
npm run dev
```

---

## 4. Biến môi trường (`.env`) — mỗi người tự tạo, KHÔNG commit lên Git

File `.env.example` là mẫu, mỗi thành viên copy thành `.env` riêng và điền
giá trị thật. File `.env` đã được thêm vào `.gitignore` để tránh lộ mật
khẩu/API key lên GitHub công khai.

---

## 5. Thứ tự chạy khi bắt đầu 1 buổi code

```bash
docker compose up -d mysql       # 1. bật database trước
cd backend && uvicorn app.main:app --reload --port 8000 &   # 2. bật backend
cd ai-service && uvicorn app.main:app --reload --port 8001 & # 3. bật AI service
cd frontend && npm run dev       # 4. bật frontend cuối cùng
```
