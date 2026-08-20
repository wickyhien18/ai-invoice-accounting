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

## 4. Biến môi trường (`.env`) — hướng dẫn chi tiết

### 4.1. `.env` là gì và vì sao cần

File `.env` chứa các thông tin **nhạy cảm hoặc dễ thay đổi giữa các máy**
(mật khẩu database, API key, cổng chạy...) — tách riêng khỏi code để:

- Không lộ mật khẩu/API key khi đẩy code lên GitHub công khai
- Mỗi thành viên có thể dùng giá trị khác nhau (VD: API key riêng) mà
  không ảnh hưởng code chung

File `.env.example` là **bản mẫu** (không chứa giá trị thật, an toàn để
commit lên Git). Mỗi thành viên tự copy thành `.env` (file này đã nằm
trong `.gitignore`, Git sẽ **không** đẩy nó lên GitHub).

### 4.2. Copy file `.env` cho từng thành phần

```bash
# Root (cho docker-compose đọc MySQL)
cp .env.example .env

# Backend
cd backend
cp .env.example .env
cd ..

# AI Service
cd ai-service
cp .env.example .env
cd ..
```

### 4.3. Giải thích từng biến trong `.env` (root — dùng cho MySQL)

| Biến                            | Ý nghĩa                                                                  | Có cần đổi không                                                            |
| ------------------------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| `MYSQL_ROOT_PASSWORD`           | Mật khẩu tài khoản `root` (toàn quyền) của MySQL                         | Nên đổi trước khi nộp bài/deploy thật, để mặc định khi chạy local cũng được |
| `MYSQL_DATABASE`                | Tên database sẽ tự tạo khi MySQL khởi động lần đầu                       | Giữ nguyên `ai_invoice_db` để khớp với `backend/.env`                       |
| `MYSQL_USER` / `MYSQL_PASSWORD` | Tài khoản riêng cho ứng dụng dùng (không dùng `root` để kết nối từ code) | Giữ nguyên khi chạy local, đổi khi deploy thật                              |

### 4.4. Giải thích từng biến trong `backend/.env`

| Biến                                  | Ý nghĩa                                                                                                                                     |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `DB_HOST`                             | Địa chỉ MySQL — để `localhost` vì chạy Docker map cổng ra máy local                                                                         |
| `DB_PORT`                             | Cổng MySQL, mặc định `3306`                                                                                                                 |
| `DB_USER` / `DB_PASSWORD` / `DB_NAME` | **Phải khớp chính xác** với giá trị đã đặt trong `.env` ở root (mục 4.3) — sai 1 ký tự sẽ báo lỗi "Access denied" khi backend kết nối MySQL |
| `SECRET_KEY`                          | Chuỗi bí mật để mã hóa JWT token (đăng nhập). Đổi thành chuỗi random dài, không dùng chung giữa các thành viên khi deploy thật              |
| `AI_SERVICE_URL`                      | Địa chỉ backend gọi sang AI service, mặc định `http://localhost:8001` — chỉ đổi nếu chạy AI service ở cổng khác                             |

### 4.5. Giải thích từng biến trong `ai-service/.env`

| Biến                             | Ý nghĩa                                                                                                                         |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `GOOGLE_APPLICATION_CREDENTIALS` | Đường dẫn tới file JSON key của Google Cloud Vision API (nếu dùng OCR qua Google). Bỏ trống nếu dùng Tesseract offline thay thế |
| `LLM_API_KEY`                    | API key của OpenAI/Claude — dùng để gọi LLM parse dữ liệu hóa đơn. **Tuyệt đối không commit key thật lên Git**                  |
| `LLM_MODEL`                      | Tên model LLM sẽ gọi, VD `gpt-4o-mini`                                                                                          |

### 4.6. Lỗi thường gặp liên quan `.env`

- **Backend báo "Access denied for user"** → `DB_USER`/`DB_PASSWORD` trong
  `backend/.env` không khớp với `.env` ở root — kiểm tra lại cho giống nhau
- **Chạy `docker compose up` nhưng không đọc được `.env`** → phải chạy lệnh
  ngay tại thư mục gốc repo (nơi có file `.env` và `docker-compose.yml`),
  không chạy từ thư mục con
- **Đổi `.env` xong nhưng MySQL không cập nhật mật khẩu mới** → MySQL chỉ
  đọc `MYSQL_ROOT_PASSWORD`/`MYSQL_PASSWORD` ở **lần đầu tạo container**.
  Nếu đổi sau khi đã chạy, cần `docker compose down -v` (xóa volume) rồi
  `docker compose up -d mysql` lại để MySQL khởi tạo lại từ đầu với giá trị mới
- **Lỡ commit `.env` thật lên GitHub** → đổi ngay mật khẩu/API key đó (coi
  như đã lộ), sau đó xóa khỏi lịch sử Git bằng `git rm --cached .env`
  rồi commit lại

---

## 5. Thứ tự chạy khi bắt đầu 1 buổi code

```bash
docker compose up -d mysql       # 1. bật database trước
cd backend && uvicorn app.main:app --reload --port 8000 &   # 2. bật backend
cd ai-service && uvicorn app.main:app --reload --port 8001 & # 3. bật AI service
cd frontend && npm run dev       # 4. bật frontend cuối cùng
```
