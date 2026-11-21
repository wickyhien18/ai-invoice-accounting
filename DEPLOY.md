# Hướng dẫn deploy (tất cả đều dùng gói miễn phí)

Sơ đồ: **Vercel** (frontend) → **Render** (backend FastAPI) → **TiDB Cloud** (MySQL) và → **Hugging Face Spaces** (ai-service: PaddleOCR, bge-m3, Gemini).
Làm theo đúng thứ tự 1 → 4, vì mỗi bước cần địa chỉ của bước trước.

## Trước khi bắt đầu
- Đẩy code này lên GitHub (`git add . && git commit && git push`). Các host bên dưới đều lấy code từ GitHub.
- Chuẩn bị `GEMINI_API_KEY` (Google AI Studio). Không bao giờ commit khóa này.
- Chỉ dùng hóa đơn giả hoặc đã che thông tin trên bản deploy công khai (Gemini gói miễn phí có thể dùng dữ liệu gửi lên để cải thiện sản phẩm).

## 1. Cơ sở dữ liệu: TiDB Cloud Serverless (tương thích MySQL)
1. Đăng ký tại tidbcloud.com, tạo cluster **Serverless** (gói Starter, miễn phí).
2. Bấm **Connect**, chọn "General", ghi lại: `HOST`, `PORT` (4000), `USERNAME` (có tiền tố dạng `xxxx.root`), `PASSWORD`.
3. Mở **SQL Editor** và chạy: `CREATE DATABASE ai_invoice_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`

## 2. ai-service: Hugging Face Spaces
1. Tạo tài khoản huggingface.co, **New Space** → SDK **Docker** → để Public hoặc Private đều được.
2. Đưa nội dung thư mục `ai-service/` lên Space (clone Space về, copy nội dung `ai-service/` vào gốc Space, push). Thêm vào đầu file `README.md` của Space:
   ```
   ---
   title: ai-invoice-ai-service
   sdk: docker
   app_port: 7860
   ---
   ```
3. Space → **Settings → Variables and secrets**, thêm: `GEMINI_API_KEY` (Secret), `LLM_MODEL`, `LLM_DAILY_LIMIT=18`, `LLM_MIN_INTERVAL=13` (giống `.env`).
4. Chờ build xong (lần đầu 10–20 phút vì tải PaddlePaddle). Địa chỉ dạng `https://<user>-<space>.hf.space`; kiểm tra `…/health` trả về `ok`.

## 3. Backend: Render
1. Đăng ký render.com, **New → Blueprint**, chọn repo GitHub này (file `render.yaml` ở gốc).
2. Điền các biến để trống (`sync: false`):
   - `DB_HOST`, `DB_USER`, `DB_PASSWORD`: lấy ở bước 1
   - `AI_SERVICE_URL`: địa chỉ Space ở bước 2 (không có dấu `/` cuối)
   - `CORS_ORIGINS`: để tạm `http://localhost:5173`, sẽ sửa lại ở bước 4
3. Deploy. Backend tự chạy `alembic upgrade head` và nạp dữ liệu demo lần đầu (`SEED_DEMO=1`: tài khoản `ktv@demo.local / ktv12345` và `ktt@demo.local / ktt12345`). Sau khi nạp xong nên đổi `SEED_DEMO` thành `0` và đổi mật khẩu demo nếu để công khai.
4. Kiểm tra `https://<tên>.onrender.com/api/health`.

## 4. Frontend: Vercel
1. Vercel → **Add New Project** → chọn repo, **Root Directory** = `frontend` (Framework: Vite).
2. Thêm biến môi trường `VITE_API_BASE` = địa chỉ backend ở bước 3 (không có `/` cuối) rồi Deploy.
3. Quay lại Render, sửa `CORS_ORIGINS` thành địa chỉ Vercel (ví dụ `https://ten-app.vercel.app`), để Render deploy lại.

## Giới hạn cần biết
- **Ngủ khi không dùng:** Render free tắt sau ~15 phút không có truy cập, lần mở đầu chậm khoảng 1 phút; Hugging Face Space free ngủ sau ~48 giờ.
- **File hóa đơn tải lên mất khi backend khởi động lại** (ổ đĩa Render free không bền; mặc định lưu ở `/tmp/uploads`). Bản demo vẫn chạy, nhưng hóa đơn tải lên mới sẽ mất ảnh gốc sau khi khởi động lại. Muốn bền thì cần lưu file ngoài (S3, Cloudflare R2...), hiện chưa làm.
- **Chưa kiểm thử trên host thật:** các Dockerfile và migration trên TiDB chưa được chạy thử trong môi trường này. Lỗi thường gặp: migration không chạy trên TiDB (xem log Render), Space hết RAM khi nạp bge-m3 lần đầu.
- Lần đầu gọi đối chiếu PO, ai-service phải tải mô hình bge-m3 (~2 GB) nên rất chậm.
