---
Hub: "[[MOC - AI & ML]]"
created: 2026-09-07
status: active
repo: https://github.com/wickyhien18/ai-invoice-accounting
---

# Ý tưởng dự án

Hệ thống AI hỗ trợ nhập liệu hóa đơn/chứng từ cho kế toán — đồ án tốt nghiệp nhóm 3 sinh viên năm 4 CNTT (UTC Hà Nội). Mục tiêu: tự động hóa việc đọc, trích xuất, đối chiếu và gán bút toán cho hóa đơn, giảm thời gian nhập liệu thủ công và sai sót cho kế toán viên.

7 nghiệp vụ cốt lõi: (1) OCR số hóa hóa đơn, (2) trích xuất dữ liệu có cấu trúc, (3) hiểu ngữ cảnh (NLP), (4) chấm điểm độ tin cậy, (5) đối chiếu chứng từ (2-way/3-way matching), (6) gán bút toán (GL Coding) theo Thông tư 133/2016/TT-BTC, (7) phân tích & báo cáo xu hướng chi tiêu.

Định hướng kỹ thuật: dùng AI có sẵn qua API (OCR cloud + LLM), không tự train model — đảm bảo máy chạy nhẹ, triển khai được trong ~4 tháng.

# Tech Stack

|Nhóm|Thành phần|Công nghệ|Lý do chọn|
|---|---|---|---|
|Nền tảng|AI Service|Python 3.12 + FastAPI, Pillow|Cùng ngôn ngữ với backend; Python 3.14 chưa có gói cài sẵn cho một số thư viện|
|Nền tảng|Backend|Python + FastAPI, SQLAlchemy, Alembic, JWT, bcrypt, PyMySQL|ORM + migration rõ ràng cho 3 người cùng code; JWT/bcrypt cho đăng nhập và phân quyền kế toán viên, kế toán trưởng|
|Nền tảng|Frontend|React + Vite + Tailwind CSS (Node.js 20 LTS)|Yêu cầu ban đầu của người dùng, hệ sinh thái phổ biến|
|Nền tảng|Database|MySQL 8.0 (Docker), DECIMAL(18,2) cho số tiền|Đồng bộ phiên bản giữa 3 máy, không sai số làm tròn|
|Nền tảng|Môi trường|Docker Compose, một file `.env` ở root|Đồng bộ cấu hình 3 máy|
|Nền tảng|Mã nguồn|Git + GitHub, ruleset nhánh main (không xóa nhánh, không force push, bắt buộc PR)|Phù hợp quy mô nhóm 3 người|
|Nền tảng|Đầu vào|Đọc trực tiếp file XML hóa đơn điện tử người dùng tải lên|Không có API hoadondientu công khai; XML không cần OCR|
|Nền tảng|Đầu ra|Google Sheet/Excel (bảng kê mẫu 01-2/GTGT), thư viện ghi: openpyxl cho Excel, Google Sheets API cho Sheet (đề xuất, chưa chốt)|Chốt cách ghi tích hợp là Google Sheet/Excel|
|Nền tảng|Sơ đồ|PlantUML, dbdiagram.io (DBML)|Sửa chữ là hình tự cập nhật|
|AI|OCR (NV1)|PaddleOCR (local)|Có mô hình tiếng Việt, đủ phát hiện + nhận dạng, miễn phí không giới hạn trang|
|AI|LLM (NV1, NV4, NV7)|Gemini Flash qua free tier|Trích 5 trường trọng yếu thành JSON, gợi ý định khoản người bán mới, tóm tắt báo cáo; không cần GPU|
|AI|Chuẩn hóa tên công ty, địa chỉ (NV2, NV5)|RapidFuzz|Chạy CPU, miễn phí|
|AI|Phân loại tài liệu đầu vào (NV1)|Logistic Regression (scikit-learn)|Chạy CPU, đơn giản|
|AI|Gợi ý định khoản Nợ/Có (NV4)|TF-IDF + Logistic Regression (scikit-learn)|Chạy CPU; đặc trưng là người bán, thuế suất, tổng tiền, lịch sử định khoản|
|AI|So khớp đơn đặt hàng (NV5)|bge-m3 (sentence-transformers)|Chạy được trên CPU, hỗ trợ đa ngôn ngữ|
|AI|Phát hiện bất thường, hóa đơn trùng (NV6)|Isolation Forest (scikit-learn)|Chạy CPU, thể hiện phần ML khi thuyết trình|

# Nhật ký kỹ thuật

## Giai đoạn 1 — Xác định đề tài và phạm vi nghiệp vụ

**Mục tiêu giai đoạn:** Làm rõ hệ thống làm gì, AI đóng vai trò gì, đâu là phần bắt buộc phải có AI và đâu là phần logic nghiệp vụ thông thường.

**Đã làm:**

- Xác định 7 nghiệp vụ cốt lõi có AI: OCR, trích xuất ML, NLP, confidence scoring, matching, GL Coding, phân tích/báo cáo
- Liệt kê baseline không-AI tương ứng (nhập tay, mapping cố định, đối chiếu chính xác tuyệt đối) làm phương án dự phòng an toàn
- Tìm nguồn tham khảo quốc tế (Ramp, Precoro, Tipalti, HighRadius, Box, EverWorker) và nguồn Việt Nam (MISA AMIS) cho từng nghiệp vụ

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** làm đầy đủ AI thật (tự train OCR/NLP) hay dùng AI có sẵn qua API
- **Đã chọn:** Phương án A — dùng API cloud (Google Vision, LLM API), không train model riêng
- **Vì sao:** phù hợp thời gian 4 tháng và yêu cầu "cấu hình máy không nặng"; chỉ 2/7 nghiệp vụ (OCR + LLM parse) thực sự cần AI, còn lại là logic code thông thường

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- Chưa quyết định nền tảng triển khai cuối cùng: web hay app di động — tạm chốt ưu tiên web trước, app là mở rộng sau nếu còn thời gian

## Giai đoạn 2 — Thiết kế kiến trúc & cấu trúc thư mục repo

**Mục tiêu giai đoạn:** Dựng khung dự án ban đầu (monorepo 3 service) để nhóm bắt đầu code, đặt tên repo GitHub.

**Đã làm:**

- Đặt tên repo: `ai-invoice-accounting`
- Tạo cấu trúc thư mục: `ai-service/`, `backend/`, `frontend/`, `database/`, `docs/` (6 thư mục con tương ứng 6 chương báo cáo)
- Viết README.md tổng quan, README riêng cho từng service
- Thêm `.gitignore` chuẩn cho Python + Node

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** đặt tên repo trùng hoặc liên quan đến các dự án cũ (pharmacy-fullstack, steam-tinder) hay không
- **Đã chọn:** `ai-invoice-accounting` — tên độc lập, không liên quan dự án trước
- **Vì sao:** tránh nhầm lẫn ngữ cảnh giữa các đồ án/dự án cá nhân khác nhau

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- Lúc này backend/frontend/database vẫn chưa chốt công nghệ cụ thể, README ghi tạm "chưa chốt"

## Giai đoạn 3 — Chốt công nghệ cụ thể và scaffold code

**Mục tiêu giai đoạn:** Chốt chính xác từng công nghệ cho từng thành phần và tạo code khởi tạo (scaffold) chạy được ngay.

**Đã làm:**

- Chốt: Backend = Python FastAPI, Frontend = React + Tailwind CSS, Database = MySQL, AI Service = Python (đồng nhất với backend)
- Tạo scaffold backend: `app/main.py`, `app/database.py`, `requirements.txt` (fastapi, sqlalchemy, pymysql, alembic, JWT, bcrypt...)
- Tạo scaffold AI service: `app/main.py`, `requirements.txt` (fastapi, pillow, pytesseract, google-cloud-vision...)
- Tạo scaffold frontend: Vite + React + Tailwind (`package.json`, `vite.config.js`, `tailwind.config.js`, `App.jsx` chạy được ngay)
- Viết `docker-compose.yml` chạy MySQL 8.0 với charset `utf8mb4` cấu hình sẵn

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** cài MySQL trực tiếp lên từng máy hay chạy qua Docker
- **Đã chọn:** Docker (docker-compose cho MySQL)
- **Vì sao:** đảm bảo cả 3 thành viên chạy đúng 1 phiên bản MySQL giống hệt nhau, tránh lỗi "máy tui chạy được, máy bạn không" do lệch charset/version
- **Vấn đề:** dùng kiểu dữ liệu nào cho số tiền trong MySQL
- **Đã chọn:** `DECIMAL(18,2)`, không dùng FLOAT/DOUBLE
- **Vì sao:** tránh sai số làm tròn — hệ thống kế toán không được phép sai lệch số liệu dù nhỏ

**Bug gặp phải (nếu có) — đánh số theo thứ tự toàn dự án, không reset theo giai đoạn:**

- **Bug 1 — Lỗi build wheel pydantic-core/pillow trên Python 3.14:** Chạy `pip install -r requirements.txt` trong `ai-service` báo lỗi build wheel thất bại cho `pillow` và `pydantic-core` → Nguyên nhân thật sự: máy dùng Python 3.14 (quá mới), các thư viện chưa có pre-built wheel, pip phải compile từ source bằng Rust (PyO3) nhưng PyO3 0.22.2 chưa hỗ trợ Python 3.14 → Cách sửa: xóa venv, tạo lại bằng Python 3.12 (`python3.12 -m venv venv`), cài lại `pip install -r requirements.txt`

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- Chưa viết endpoint thật cho `/ocr` và `/extract` trong AI Service — mới có `/health` placeholder

## Giai đoạn 4 — Quản lý biến môi trường (.env) và bảo mật cấu hình

**Mục tiêu giai đoạn:** Chuẩn hóa cách quản lý secret/cấu hình giữa 3 service, tránh rối khi 3 thành viên cùng setup máy riêng.

**Đã làm:**

- Ban đầu tạo 3 file `.env.example` riêng (root cho MySQL, backend, ai-service) — sau đó phát hiện gây trùng lặp và dễ lệch dữ liệu
- Consolidate lại thành **1 file `.env.example` duy nhất ở root**, chứa toàn bộ biến cho MySQL + backend + AI service
- Sửa `backend/app/database.py` và `ai-service/app/main.py` để tự động load `.env` gốc qua đường dẫn tương đối (`Path(__file__).resolve().parent.parent.parent / ".env"`)
- Viết chi tiết trong SETUP.md: ý nghĩa từng biến, các lỗi thường gặp khi `.env` bị lệch giữa `DB_USER`/`MYSQL_USER`...

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** giữ 3 file `.env` riêng theo từng service, hay gộp thành 1 file duy nhất
- **Đã chọn:** gộp thành 1 file `.env` duy nhất ở root
- **Vì sao:** 3 file riêng dễ bị lệch giá trị (VD: sửa MySQL_PASSWORD ở root nhưng quên sửa DB_PASSWORD ở backend) → gây lỗi "Access denied" khó debug; 1 file duy nhất loại bỏ hoàn toàn nguy cơ này

**Bug gặp phải (nếu có) — đánh số theo thứ tự toàn dự án, không reset theo giai đoạn:**

- **Bug 2 — File `.env.example` cũ bị dùng nhầm:** Người dùng tải nhầm bản `.env.example` cũ (4 dòng, tiếng Việt, tên file `_env.example`) từ một lần tải trước đó → Nguyên nhân thật sự: file cũ vẫn còn trong thư mục uploads của người dùng, không phải lỗi từ phía service → Cách sửa: đối chiếu MD5 hai file để xác nhận khác nhau, hướng dẫn tải lại đúng zip mới nhất chứa file `.env.example` đã consolidate (23 dòng, tiếng Anh)

## Giai đoạn 5 — Chuyển ngôn ngữ tài liệu dự án

**Mục tiêu giai đoạn:** Thử chuẩn hóa toàn bộ tài liệu kỹ thuật (README, SETUP.md, comment code) sang tiếng Anh, sau đó quay lại tiếng Việt theo yêu cầu thực tế của người dùng.

**Đã làm:**

- Dịch toàn bộ README.md, SETUP.md, các README con, comment trong `database.py`/`main.py` sang tiếng Anh
- Quét toàn bộ repo bằng script Python kiểm tra ký tự có dấu để đảm bảo không sót tiếng Việt
- Sau đó quay lại dùng tiếng Việt cho toàn bộ trao đổi và nội dung báo cáo đồ án (Chương 2, 3) theo yêu cầu người dùng

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** ngôn ngữ tài liệu dự án dùng tiếng Anh hay tiếng Việt
- **Đã chọn:** Code/README kỹ thuật giữ tiếng Anh (thời điểm viết); nội dung báo cáo đồ án (Chương 2 trở đi) dùng tiếng Việt
- **Vì sao:** báo cáo đồ án nộp cho hội đồng chấm tại Việt Nam, thuật ngữ kế toán (Nợ/Có, TT133...) cần chính xác bằng tiếng Việt để tránh hiểu nhầm khi bảo vệ

## Giai đoạn 6 — Cấu hình bảo vệ nhánh Git (Branch Ruleset)

**Mục tiêu giai đoạn:** Thiết lập quy tắc bảo vệ nhánh `main` trên GitHub phù hợp quy mô nhóm 3 người.

**Đã làm:**

- Tạo ruleset trên GitHub Settings → Rules cho repo `ai-invoice-accounting`
- Bật 3 rule cốt lõi: Restrict deletions, Block force pushes, Require a pull request before merging
- Bỏ qua các rule nâng cao không cần thiết cho quy mô nhỏ (signed commits, code scanning, status checks CI...)

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** bật đầy đủ mọi rule bảo vệ nhánh hay chỉ chọn lọc
- **Đã chọn:** chỉ 3 rule tối thiểu (xóa nhánh, force push, PR bắt buộc)
- **Vì sao:** nhóm 3 người không có CI/CD, không cần ký commit — bật thừa rule chỉ gây cản trở tốc độ làm việc mà không tăng thêm an toàn thực tế

## Giai đoạn 7 — Cài đặt công cụ hỗ trợ (Docker, MySQL Workbench)

**Mục tiêu giai đoạn:** Hướng dẫn cài đặt môi trường phát triển đầy đủ cho các thành viên nhóm, kể cả người chưa quen dùng terminal.

**Đã làm:**

- Viết hướng dẫn cài Python 3.12, Node.js 20 LTS, Docker theo từng hệ điều hành (Windows/Mac/Linux, riêng CachyOS/Arch)
- Viết hướng dẫn kiểm tra đã cài hay chưa (`--version` cho từng công cụ)
- Viết hướng dẫn cài và kết nối MySQL Workbench tới MySQL chạy trong Docker (`127.0.0.1:3306`) cho người muốn thao tác bằng GUI thay vì terminal

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- Chưa cài đặt Docker trên máy người dùng tại thời điểm ghi chú này — đang chờ hoàn tất bước cài đặt trước khi chạy `docker compose up`

## Giai đoạn 8 — Phân tích yêu cầu (Chương 2 báo cáo đồ án)

**Mục tiêu giai đoạn:** Xây dựng Chương 2 (Phân tích & Thiết kế hệ thống) đúng khung lý thuyết Requirement Analysis đã học (dựa theo slide môn học Project 1 — Phân tích yêu cầu).

**Đã làm:**

- Xác định 6 nhóm bên liên quan (stakeholders)
- Soạn bảng câu hỏi phỏng vấn và bảng hỏi khảo sát (elicitation)
- Thu thập danh sách tài liệu liên quan (TT133, Nghị định 70/2025/NĐ-CP, mẫu biểu chứng từ...)
- Đặc tả yêu cầu chức năng (FR-01 → FR-10) và phi chức năng (NFR-01 → NFR-05)
- Ưu tiên hóa theo MoSCoW (Must/Should/Could/Won't have)
- Mô hình hóa yêu cầu đầy đủ 5 kỹ thuật: Use Case Diagram, Activity Diagram, DFD, ERD, User Story & Acceptance Criteria (US-01 → US-14)
- Thêm mục Xác minh yêu cầu và Quản lý yêu cầu theo đúng khung slide

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** thứ tự Chương 2 và Chương 3 nên là Cơ sở lý thuyết trước hay Phân tích thiết kế trước
- **Đã chọn:** đảo lại — Chương 2 = Phân tích & Thiết kế, Chương 3 = Cơ sở lý thuyết
- **Vì sao:** theo yêu cầu trực tiếp của người dùng, khác quy ước thông thường nhưng vẫn triển khai được vì Chương 4-6 không bị ảnh hưởng bởi việc hoán đổi này
- **Vấn đề:** "User Story & Acceptance Criteria" nên là mục riêng đứng trước Đặc tả yêu cầu, hay là 1 trong 5 kỹ thuật con của Mô hình hóa yêu cầu
- **Đã chọn:** xếp vào làm mục con (2.5.5) trong Mô hình hóa yêu cầu
- **Vì sao:** đúng theo thứ tự liệt kê trong slide gốc môn học (Use Case Diagram, Activity Diagram, DFD, ERD, User Story/Acceptance Criteria đều là 5 kỹ thuật ngang hàng)

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- Cần rà lại toàn bộ định dạng trích dẫn nguồn trong Chương 2-3 theo đúng chuẩn APA 2 phần (in-text + danh mục cuối bài) thay vì kiểu liệt kê tự do "**Nguồn:** ... — link" đang dùng tạm

## Giai đoạn 9 — Thiết kế cơ sở dữ liệu (ERD) và phát hiện thiếu sót

**Mục tiêu giai đoạn:** Hoàn thiện ERD cho hệ thống, đảm bảo đủ bảng để mọi nghiệp vụ (đặc biệt đối chiếu chứng từ) hoạt động được bằng logic tự động, không chỉ là mô tả suông.

**Đã làm:**

- Thiết kế ban đầu 6 bảng: `users`, `invoices`, `invoice_fields`, `chart_of_accounts`, `journal_entries`, `matching_results`
- Vẽ ERD trực quan (SVG) và Use Case Diagram minh họa

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** bảng `matching_results` chỉ lưu `po_reference` dạng text, không có bảng PO thật để đối chiếu số liệu tự động
- **Đã chọn:** bổ sung bảng `purchase_orders` (id, po_number, vendor, order_date, expected_amount, status), sửa `matching_results.po_reference` thành khóa ngoại `po_id` trỏ đúng bảng này
- **Vì sao:** nếu không có bảng PO thật, hệ thống không thể tự động so sánh số tiền hóa đơn với đơn đặt hàng — tính năng đối chiếu (FR-06) sẽ chỉ là nhập tay, mất hết ý nghĩa "tự động" của đề tài AI
- **Vấn đề:** cách nhập dữ liệu PO vào hệ thống — có nên dùng OCR chụp ảnh như hóa đơn không
- **Đã chọn:** Cách 1 (form nhập liệu trực tiếp) + Cách 2 (import hàng loạt từ Excel/CSV), không dùng OCR cho PO
- **Vì sao:** PO do chính doanh nghiệp tự tạo ra trước khi mua hàng (không phải nhận từ bên ngoài dưới dạng ảnh như hóa đơn), nên nhập liệu trực tiếp hợp lý hơn nhiều so với việc chụp ảnh rồi OCR lại — tránh tốn chi phí API không cần thiết

**Bug gặp phải (nếu có) — đánh số theo thứ tự toàn dự án, không reset theo giai đoạn:**

- **Bug 3 — Thiếu bảng dữ liệu để đối chiếu tự động:** ERD ban đầu có `matching_results` nhưng không có nơi lưu dữ liệu PO thật (chỉ có `po_reference` là chuỗi text) → Nguyên nhân thật sự: thiết kế ERD lần đầu chỉ tập trung vào luồng xử lý hóa đơn, bỏ sót rằng đối chiếu cần 2 phía dữ liệu (hóa đơn VÀ đơn đặt hàng) → Cách sửa: bổ sung bảng `purchase_orders`, đổi `po_reference` (text) thành `po_id` (khóa ngoại), thêm cột `amount_difference` để hệ thống tự tính chênh lệch

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- Bổ sung FR-09 (nhập PO qua form) và FR-10 (import PO từ Excel/CSV) vào bảng đặc tả yêu cầu và MoSCoW — đã cập nhật văn bản nhưng **chưa vẽ lại ERD trực quan (SVG) và Use Case Diagram** với bảng/use case mới này
    - ✅ **Đã giải quyết ở Giai đoạn 12–13:** ERD chốt lại thành 9 bảng (có `purchase_orders`), use case được sửa và giải thích lại
- Cần thống nhất lại tên use case giữa bản vẽ tay của người dùng (VD: "Tải hóa đơn và nhận dạng hóa đơn", "Kiểm tra thông tin và rủi ro của hóa đơn") với danh sách use case đã viết trong Chương 2 — hiện đang lệch tên gọi giữa 2 nơi, cần đồng bộ trước khi hoàn thiện báo cáo
    - ✅ **Đã giải quyết ở Giai đoạn 12:** use case được sửa/bổ sung kèm giải thích theo đúng nghiệp vụ

## Giai đoạn 10 — Vẽ sơ đồ trực quan trên Figma

**Mục tiêu giai đoạn:** Chuyển các mô hình yêu cầu (Use Case, DFD) từ mô tả văn bản/code DBML sang sơ đồ trực quan để chèn vào báo cáo.

**Đã làm:**

- Kết nối Figma qua tài khoản người dùng (team "Hiển Giáp's team")
- Vẽ DFD mức 1 bằng Mermaid syntax trong FigJam — ban đầu dùng D1-D5 kèm `chart_of_accounts`, sau đó chỉnh lại đúng theo thứ tự đặt tên kho dữ liệu của người dùng (D1 Hóa đơn, D2 Đơn đặt hàng, D3 Đối chiếu, D4 Bút toán) và bổ sung D6 cho danh mục tài khoản (phát hiện thiếu khi đối chiếu với bản vẽ tay)
- Vẽ lại Use Case Diagram theo đúng bố cục ảnh người dùng đã vẽ tay (2 actor, mỗi actor 4 và 3 use case)

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** DFD có nên giữ kho "D5 Tổng hợp" như bản vẽ tay của người dùng hay bỏ đi
- **Đã chọn:** đề xuất bỏ D5, thay bằng luồng output trực tiếp từ tiến trình báo cáo ra Kế toán trưởng — nhưng để người dùng tự quyết định giữ nguyên hay đổi
- **Vì sao:** theo lý thuyết DFD chuẩn, kho dữ liệu (data store) phải là nơi lưu trữ lâu dài; báo cáo tổng hợp thường được tính toán lại mỗi lần từ dữ liệu bút toán, không cần lưu cố định thành kho riêng — quyết định cuối cùng vẫn chưa chốt tại thời điểm ghi chú này
    - ✅ **Chốt ở Giai đoạn 12:** bỏ hẳn DFD khỏi bộ sơ đồ (thầy nhận xét DFD/BFD thừa vì đã có Activity Diagram), nên câu hỏi D5 không còn cần thiết

## Giai đoạn 11 — Gộp báo cáo thành một file duy nhất

**Mục tiêu giai đoạn:** Gộp các phần báo cáo của nhóm thành một file Word thống nhất và bỏ các thông tin không cần thiết.

**Đã làm:**

- Gộp thành `Bao_cao_Nhom15_final.docx` (39 trang) bằng script merge từ file báo cáo nhóm `Project_1.docx`
- Giữ nguyên toàn bộ nội dung đối chiếu đơn đặt hàng (PO) và báo cáo/dashboard — nhóm đã chốt không cắt hai phần này
- Chốt cách ghi tích hợp đầu ra trong toàn bộ tài liệu là **"Google Sheet/Excel"**
- Chốt hướng không kết nối trực tiếp hoadondientu: hóa đơn điện tử không có API công khai, hệ thống nhận file người dùng tải lên, không tra cứu tự động, không xử lý captcha

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** chọn OCR engine và LLM cụ thể nào
- **Đã chọn:** chưa chọn — báo cáo so sánh 3 phương án ở Bảng 2.2: (A) API AI lớn, (B) OCR mã nguồn mở như Tesseract, (C) kết hợp
- **Vì sao:** chưa có số liệu thử nghiệm thật để chọn; tránh nêu độ chính xác không có nguồn
- **Vấn đề:** ngưỡng độ tin cậy dùng cho từng trường
- **Đã chọn:** xanh ≥ 90, vàng 70 đến dưới 90, đỏ < 70
- **Vì sao:** kế toán viên chỉ phải tập trung vào ô vàng/đỏ, ô xanh vẫn được đối chiếu nhưng ít rủi ro hơn

**Bug gặp phải (nếu có) — đánh số theo thứ tự toàn dự án, không reset theo giai đoạn:**

- **Bug 4 — Script merge Word lỗi nhiều bước:** thiếu style "Table Grid", sai chữ ký hàm phụ trợ, nhận diện sai trang của mục lục, thừa page break, dư trang trắng cuối file → Nguyên nhân thật sự: file gốc của nhóm không có đủ style/cấu trúc mà script giả định → Cách sửa: sửa từng lỗi trong script, dựng lại file đến khi hết lỗi

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- File Word hiện **đã cũ so với các quyết định ở Giai đoạn 12–14**: còn ERD 5 bảng (cần thay bằng ERD 9 bảng), còn bảng MoSCoW 3 cột, còn mục DFD, chưa có SD1/SD2, use case chưa thay hình mới. Người dùng yêu cầu tạm thời không ghi vào Word
- Bản patch bảng MoSCoW trong script merge bị lỗi cú pháp (chuỗi chứa `\n` trong heredoc), chưa áp dụng được
- Mục lục đang là mục lục tĩnh, danh sách User Story vẫn đang đánh lại số

## Giai đoạn 12 — Chốt MoSCoW và bộ sơ đồ thiết kế

**Mục tiêu giai đoạn:** Chốt cách trình bày MoSCoW và bộ sơ đồ đủ dùng, sửa use case cho đúng nghiệp vụ.

**Đã làm:**

- Đổi bảng MoSCoW: bỏ cột lý do, gom các đặc tả cùng nhóm vào một dòng (Must: FR-01, FR-02, FR-03, FR-04, FR-05, FR-07, xuất Excel/Sheet mẫu 01-2/GTGT, NFR-03/04/05; Should: FR-06, FR-09, FR-08, NFR-01/02; Could: import PO từ Excel/CSV, cảnh báo chi tiêu bất thường; Won't: kết nối trực tiếp hoadondientu, tự hạch toán không qua duyệt, app di động riêng, đọc ngược từ Sheet, tích hợp MISA/KiotViet)
- Rà lại 7 nghiệp vụ theo cách gọi của báo cáo: NV1 Tiếp nhận và bóc tách bằng AI, NV2 Kiểm tra sơ bộ, NV3 Đối chiếu song song và hiệu chỉnh, NV4 Gợi ý định khoản Nợ/Có, NV5 Đối chiếu đơn đặt hàng, NV6 Phê duyệt hai cấp, NV7 Xuất bảng kê và báo cáo
- Sửa lại Use Case Diagram kèm giải thích từng use case (include theo mũi tên dọc để tránh đè nhau)
- Vẽ hai sơ đồ tuần tự SD1, SD2 (bản đầu, sau đó được vẽ lại ở Giai đoạn 14)

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** DFD và BFD có cần giữ không (thầy nhận xét là thừa vì đã có Activity Diagram)
- **Đã chọn:** bỏ DFD và BFD; bộ sơ đồ gồm Use Case, Activity, Sequence (SD1, SD2), ERD, kiến trúc hệ thống; sơ đồ trạng thái hóa đơn là tùy chọn
- **Vì sao:** tránh trùng lặp, mỗi sơ đồ trả lời một câu hỏi khác nhau (ai làm gì / thành phần nào gọi nhau / dữ liệu lưu ở đâu)
- **Vấn đề:** có cần mô hình tuần tự không
- **Đã chọn:** có, vẽ SD1 (tiếp nhận → hiệu chỉnh) và SD2 (gửi duyệt → duyệt/từ chối → xuất)
- **Vì sao:** Activity chỉ cho thấy thứ tự công việc, không cho thấy thành phần nào ghi vào bảng nào

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- Slide NV1 ghi ngưỡng 85% trong khi báo cáo dùng 90/70 — cần thống nhất
- Slide NV2 còn câu "tự động tra cứu trên cổng thuế", mâu thuẫn với quyết định không kết nối hoadondientu — cần sửa
- Căn cứ pháp lý mẫu 01-2/GTGT: slide ghi TT119/2014, nguồn lại ghi TT156/2013 — chưa kiểm chứng, cần tra lại
- Câu "3–5 phút/chứng từ" chưa có nguồn — bỏ hoặc ghi rõ là ước tính
- Hai hình minh họa Google Sheet cần ảnh chụp thật, hiện chỉ để chỗ trống
- Câu FR-07 nên sửa thành "lưu trạng thái duyệt của hóa đơn"
- Danh sách "7 nghiệp vụ" ở đầu file nhật ký (OCR, trích xuất, NLP, độ tin cậy, đối chiếu, GL Coding, báo cáo) khác với NV1–NV7 trong báo cáo — nên thống nhất một cách gọi
- Mục "Tech Stack" và Giai đoạn 1 ghi đã chọn Phương án A (API cloud), nhưng báo cáo hiện so sánh 3 phương án mà chưa chọn — nhóm cần quyết định lại cho khớp
    - ✅ **Giải quyết một phần ở Giai đoạn 16:** OCR chốt PaddleOCR (chạy local), Tech Stack đã sửa; LLM vẫn dự kiến Gemini Flash, chưa chốt

## Giai đoạn 13 — Chốt ERD 9 bảng và từ điển dữ liệu

**Mục tiêu giai đoạn:** Chốt ERD cuối, đủ để kiểm tra tính minh bạch sổ sách, kèm từ điển dữ liệu và bảng giải thích.

**Đã làm:**

- Chốt 9 bảng, 5 cụm: `users` | `invoices`, `invoice_fields` | `chart_of_accounts`, `journal_entries` | `item_categories`, `category_aliases` | `purchase_orders`, `matching_results`
- 12 liên kết khóa ngoại; `journal_entries` có hai khóa ngoại cùng trỏ vào `chart_of_accounts` (`debit_account`, `credit_account`); `users` nối vào `invoices` ở 2 chỗ (`uploaded_by`, `approved_by`) và vào `purchase_orders` (`created_by`)
- `invoices` gồm thêm `file_path`, `file_type`, `deduct_group` và các cột trạng thái `status`, `reject_reason`, `approved_by`, `approved_at`, `export_status`, `exported_at`
- Viết DBML cho dbdiagram.io và các bảng giải thích: tổng quan 9 bảng, bảng quan hệ, từ điển từng cột, bảng giá trị `status`
- Thống nhất thứ tự trình bày ERD với thầy: `invoices` → `invoice_fields` → `item_categories`/`category_aliases` → `chart_of_accounts`/`journal_entries` → `purchase_orders`/`matching_results` → `users`

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** trạng thái duyệt lưu ở bảng nào
- **Đã chọn:** lưu ở `invoices` (`status`, `approved_by`, `approved_at`, `reject_reason`); `journal_entries` không có cột trạng thái
- **Vì sao:** duyệt là theo cả hóa đơn, không theo từng dòng bút toán
- **Vấn đề:** duyệt và xuất có chung một trạng thái không
- **Đã chọn:** tách riêng `status` và `export_status`
- **Vì sao:** ghi Sheet lỗi thì hóa đơn vẫn ở `da_duyet`, xuất lại được mà không bị ghi trùng
- **Vấn đề:** có lưu việc chia màn hình đối chiếu vào database không
- **Đã chọn:** không, lưu ở trình duyệt; bỏ cột `is_edited`
- **Vì sao:** chỉ là trạng thái giao diện; việc sửa vẫn truy được nhờ so sánh `extracted_value` với `final_value`
- **Vấn đề:** có lưu file hóa đơn gốc không
- **Đã chọn:** có, thêm lại `file_path` và `file_type`
- **Vì sao:** cần xem lại chứng từ gốc khi duyệt và kiểm tra sổ sách; `file_type` quyết định đọc XML trực tiếp hay gọi AI
- **Vấn đề:** có cần phân nhóm theo mẫu 01-2/GTGT không
- **Đã chọn:** thêm `deduct_group` vào `invoices`
- **Vì sao:** để xếp hóa đơn vào đúng nhóm khi kê khai thuế

**Bug gặp phải (nếu có) — đánh số theo thứ tự toàn dự án, không reset theo giai đoạn:**

- **Bug 5 — Làm mất bảng PO khi thay ERD trong báo cáo:** Khi gộp file, ERD 7 bảng của nhóm bị thay bằng bản 5 bảng → Nguyên nhân thật sự: bản 5 bảng được vẽ để gọn nhưng không có `purchase_orders` và `matching_results`, trong khi nhóm đã chốt giữ PO → Cách sửa: dùng ERD 9 bảng chốt ở giai đoạn này; chưa cập nhật vào file Word
- **Bug 6 — Gợi ý sai vị trí lưu trạng thái duyệt:** Ban đầu gợi ý đặt trạng thái duyệt ở `journal_entries` → Nguyên nhân thật sự: nhầm đơn vị duyệt (theo dòng bút toán thay vì theo hóa đơn) → Cách sửa: chuyển toàn bộ sang `invoices`

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- Chưa liệt kê giá trị cụ thể của `deduct_group` theo mẫu 01-2/GTGT thật
- `purchase_orders.status` chưa định nghĩa chính thức (đề xuất: đang mở, đã đối chiếu)
- Cần chặn truy cập `file_path`: chỉ người dùng đã đăng nhập mới mở được file hóa đơn (là chứng từ tài chính)
- Chưa viết migration Alembic và model SQLAlchemy cho 9 bảng
- Chưa cập nhật ERD mới vào báo cáo Word

## Giai đoạn 14 — Vẽ lại Activity, SD1, SD2 bằng PlantUML

**Mục tiêu giai đoạn:** Kiểm tra Activity và SD sau khi chốt ERD, vẽ lại cho khớp và có cách vẽ lại được.

**Đã làm:**

- Rà Activity cũ (dạng flowchart không làn) và tìm 6 chỗ lệch ERD/thiết kế chốt: không có swimlane; không rẽ nhánh theo `file_type`; độ tin cậy chỉ 2 nhánh Thấp/Cao; đối chiếu PO luôn chạy; thiếu bước xuất sang Google Sheet/Excel; vòng từ chối không đi qua kế toán viên gửi lại
- Vẽ lại Activity có 3 làn (Kế toán viên, Hệ thống/AI, Kế toán trưởng)
- Đặt tên: **SD1 — Tiếp nhận, bóc tách bằng AI và hiệu chỉnh hóa đơn** (NV1–NV3); **SD2 — Gửi duyệt, phê duyệt hai cấp và xuất bảng kê** (NV4–NV7)
- Xuất 3 file `.puml` và 3 ảnh PNG; viết sẵn lời thuyết trình cho từng sơ đồ và các câu thầy có thể hỏi

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** công cụ vẽ sơ đồ
- **Đã chọn:** PlantUML (dán code vào plantuml.com, xuất PNG/SVG); draw.io là phương án thay thế khi cần kéo thả tay
- **Vì sao:** sửa chữ là hình tự cập nhật, đúng chuẩn UML, có swimlane và khung `alt`/`opt`; thử Mermaid trước nhưng swimlane không đúng chuẩn (các làn xếp cạnh nhau, hình rất dài)

**Bug gặp phải (nếu có) — đánh số theo thứ tự toàn dự án, không reset theo giai đoạn:**

- **Bug 7 — Mermaid báo lỗi cú pháp ở SD2:** render sequence diagram thất bại → Nguyên nhân thật sự: dấu `;` trong nội dung tin nhắn bị Mermaid hiểu là dấu ngắt lệnh → Cách sửa: thay `;` bằng dấu phẩy (sau đó chuyển hẳn sang PlantUML)
- **Bug 8 — Ảnh PNG bị chìm chữ khi xem ở chế độ tối:** hộp sáng, chữ sáng trên nền đen → Nguyên nhân thật sự: PNG xuất ra có nền trong suốt, trình xem tô nền đen → Cách sửa: thêm `skinparam backgroundColor white` vào đầu file `.puml`, kiểm tra pixel góc ảnh là trắng

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- Activity và SD2 lệch thứ tự: Activity cho hệ thống gợi ý định khoản **trước** khi kế toán viên bấm xác nhận, còn SD2 bắt đầu từ lúc xác nhận rồi mới ghi `journal_entries` — cần chọn một cách và vẽ lại cho khớp
- Tên làn "Hệ thống/AI" đang gộp backend và AI service, tách ra nếu thầy yêu cầu
- Ví dụ bút toán "Nợ 6422 / Có 331" chỉ minh họa cho hóa đơn mua hàng có VAT
- Chưa thay hình mới (use case, Activity, SD1, SD2, ERD) vào báo cáo Word
- Sơ đồ trạng thái hóa đơn (tùy chọn) chưa vẽ
- Chưa có ảnh chụp Google Sheet thật, chưa có số liệu thử nghiệm OCR/LLM

## Giai đoạn 15 — Thêm mục "Công nghệ áp dụng" vào báo cáo

**Mục tiêu giai đoạn:** Đưa danh sách model/công nghệ miễn phí mà nhóm đã tra cứu (tháng 10/2026) vào báo cáo Word, để phần công nghệ có căn cứ thay vì để trống.

**Đã làm:**

- Thêm mục **7. Công nghệ áp dụng** vào cuối Chương 2 (sau 6.4 ERD) trong `Project_1.docx`, gồm 7.1 Danh sách công nghệ theo từng khâu nghiệp vụ (13 dòng: OCR, LLM, ML/NLP, FPT.AI Reader chưa rõ chi phí), 7.2 Bộ công nghệ tối thiểu để chạy trọn đồ án (OCR: PaddleOCR/VietOCR + Azure F0 để so sánh; LLM: Gemini Flash free tier; ML riêng: TF-IDF + Logistic Regression, Isolation Forest, bge-m3), 7.3 Lưu ý khi áp dụng
- Cập nhật mục lục tĩnh (4 dòng mới, trang 41–44), kiểm tra bằng cách render PDF: heading 6.4 vẫn ở trang 36 như mục lục cũ
- Giữ nguyên mọi phần khác của file Word

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** viết mục này như kết luận đã chọn công nghệ, hay như danh sách ứng viên
- **Đã chọn:** viết là danh sách ứng viên, ghi rõ chưa chốt phương án OCR/LLM cuối cùng
- **Vì sao:** khớp với Bảng 2.2 trong báo cáo (so sánh 3 phương án mà chưa chọn) và vì free tier thay đổi thường xuyên, chưa có số liệu thử nghiệm thật
- **Vấn đề:** đặt mục mới ở đâu trong báo cáo
- **Đã chọn:** mục 7 của Chương 2, sau phần mô hình hóa yêu cầu
- **Vì sao:** Chương 2 là Phân tích và Thiết kế, công nghệ áp dụng đứng sau yêu cầu và mô hình; nếu nhóm muốn đưa sang Chương 3 hoặc Chương 4 thì chuyển được

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- Mục "Tech Stack" ở đầu file này ghi Google Cloud Vision/Tesseract và GPT-4o-mini/Claude, còn danh sách mới chủ yếu là PaddleOCR/VietOCR, Gemini Flash, Azure F0 — cần thống nhất lại cho khớp khi nhóm chốt công nghệ
    - ✅ **Giải quyết một phần ở Giai đoạn 16:** Tech Stack đã sửa theo PaddleOCR; phần LLM chưa chốt
- Số liệu free tier của Gemini lấy từ bài tổng hợp bên thứ ba (đến 30/09/2026), các nguồn lệch nhau; cần xem hạn mức thực tế tại ai.google.dev/gemini-api/docs/rate-limits trước khi chốt
- Dữ liệu gửi Gemini free tier có thể bị Google dùng cải thiện sản phẩm: chỉ gửi hóa đơn mẫu hoặc đã che mã số thuế và tên doanh nghiệp
- Chưa kiểm tra license từng bản phát hành của các model mã nguồn mở (đặc biệt LayoutLMv3 hạn chế thương mại)
- FPT.AI Reader chưa có bảng giá công khai, cần xem trực tiếp trên reader.fpt.ai
- Mục lục Word vẫn là mục lục tĩnh, số trang cần cập nhật tay khi nội dung đổi

## Giai đoạn 16 — Chọn OCR và bổ sung công nghệ backend/frontend vào báo cáo

**Mục tiêu giai đoạn:** Mục "Công nghệ áp dụng" ở Giai đoạn 15 mới chỉ có công nghệ AI dạng danh sách ứng viên; cần chọn một OCR cụ thể và đưa nốt các công nghệ còn lại (backend, frontend, cơ sở dữ liệu, môi trường) vào báo cáo.

**Đã làm:**

- Sắp xếp lại mục 7 của `Project_1.docx` thành 5 mục: 7.1 Công nghệ sử dụng trong hệ thống (bảng 12 dòng: AI Service gồm OCR/LLM/ML/nền tảng, Backend, Frontend, Cơ sở dữ liệu, Môi trường, Quản lý mã nguồn, Đầu vào XML, Đầu ra Sheet/Excel, Công cụ vẽ sơ đồ), 7.2 Lựa chọn công cụ OCR: PaddleOCR, 7.3 Danh sách công nghệ AI ứng viên (bảng 13 dòng cũ), 7.4 Bộ công nghệ AI tối thiểu, 7.5 Lưu ý khi áp dụng
- Cập nhật mục lục tĩnh (6 dòng, trang 41–46); render PDF kiểm tra, heading 6.4 vẫn ở trang 36
- Sửa bảng "Tech Stack" ở đầu file này cho khớp
- Kiểm tra tài liệu PaddleOCR: tiếng Việt (mã `vi`) nằm trong mô hình `latin_PP-OCRv5_mobile_rec` của PP-OCRv5

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** chọn OCR chính trong PaddleOCR, VietOCR, EasyOCR, Tesseract, Docling, Azure F0, Donut/LayoutLMv3, FPT.AI Reader
- **Đã chọn:** PaddleOCR (chạy local)
- **Vì sao:** có mô hình tiếng Việt, là bộ OCR đủ cả phát hiện vùng chữ lẫn nhận dạng (VietOCR chỉ nhận dạng nên phải ghép thêm bộ phát hiện), mã nguồn mở không giới hạn số trang, hóa đơn thật không phải gửi ra ngoài ở bước đọc chữ, cùng ngôn ngữ Python với AI Service. Đánh đổi: chỉ trả về chữ, cần LLM hoặc quy tắc để ra các trường; Azure F0 giữ lại để đối chứng nếu cần (500 trang/tháng), Tesseract/EasyOCR làm dự phòng, Docling xét thêm nếu bảng dòng hàng hóa đọc kém
- **Vấn đề:** hóa đơn điện tử XML có cần qua OCR không
- **Đã chọn:** đọc trực tiếp file XML, không qua OCR
- **Vì sao:** dữ liệu đã có cấu trúc sẵn, tránh sai số OCR; khớp với `file_type` trong bảng `invoices`

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- Chưa có số liệu thử nghiệm: cần chạy PaddleOCR trên bộ hóa đơn mẫu của nhóm và đo tỷ lệ đọc đúng từng trường (số hóa đơn, ngày, mã số thuế, tổng tiền, thuế suất) trước khi coi lựa chọn này là chốt
- LLM (dự kiến Gemini Flash free tier) chưa chốt; dữ liệu gửi lên chỉ là hóa đơn mẫu hoặc đã che mã số thuế và tên doanh nghiệp
- Thư viện ghi Google Sheet và xuất Excel chưa chốt
- Bảng ở mục 7.1 và 7.3 của báo cáo có vài dòng giống nhau về nội dung, nhóm có thể rút gọn 7.3 nếu báo cáo quá dài

## Giai đoạn 17 — Chốt bảng công nghệ áp dụng cho toàn dự án

**Mục tiêu giai đoạn:** Có một bảng công nghệ duy nhất cho cả dự án (nền tảng + AI), mỗi vai trò AI chỉ chọn một công nghệ từ danh sách model miễn phí của nhóm.

**Đã làm:**

- Gộp công nghệ nền tảng (AI Service, Backend, Frontend, Database, môi trường, mã nguồn, đầu vào/ra, sơ đồ) và công nghệ AI thành một bảng ở mục Tech Stack đầu file
- Chọn mỗi vai trò AI một công nghệ: OCR = PaddleOCR; LLM = Gemini Flash (free tier); chuẩn hóa tên = RapidFuzz; phân loại tài liệu = Logistic Regression; gợi ý định khoản = TF-IDF + Logistic Regression; so khớp PO = bge-m3; phát hiện bất thường = Isolation Forest
- Không chọn: PhoBERT, XGBoost/LightGBM, Docling, Donut/LayoutLMv3, Azure F0, Qwen/Gemma/Llama local, EasyOCR, Tesseract, VietOCR, FPT.AI Reader (giữ làm dự phòng hoặc đối chứng)
- Nhóm quyết định **không ghi mục "Công nghệ áp dụng" vào file Word nữa**: mục 7 trong bản `Project_1.docx` đã gửi ở Giai đoạn 15–16 không dùng, giữ file Word gốc của nhóm

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** LLM chọn Gemini Flash qua API hay model local (Qwen-VL, Gemma, Llama qua Ollama)
- **Đã chọn:** Gemini Flash free tier
- **Vì sao:** model local cần GPU hoặc máy đủ RAM, bản nhỏ chạy CPU chậm, mà yêu cầu là máy không nặng. Đánh đổi: dữ liệu gửi lên có thể được Google dùng cải thiện sản phẩm, chỉ gửi hóa đơn mẫu hoặc đã che mã số thuế và tên doanh nghiệp; hạn mức free tier thay đổi thường xuyên
- **Vấn đề:** có dùng PhoBERT và XGBoost/LightGBM không
- **Đã chọn:** chưa dùng
- **Vì sao:** PhoBERT fine-tune nên có GPU; TF-IDF + Logistic Regression đã đủ cho gợi ý định khoản và đơn giản hơn để giải thích khi bảo vệ. Có thể nâng cấp sau nếu độ chính xác chưa đạt

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- Chưa thử nghiệm: cần chạy PaddleOCR và Gemini Flash trên bộ hóa đơn mẫu, đo tỷ lệ đọc đúng từng trường
- Thư viện ghi Sheet/Excel (openpyxl, Google Sheets API) là đề xuất, chưa chốt
- Hạn mức Gemini free tier lấy từ nguồn bên thứ ba (đến 30/09/2026), cần xem lại tại ai.google.dev/gemini-api/docs/rate-limits trước khi dùng
- Chưa kiểm tra license từng bản phát hành của các model mã nguồn mở
- Chưa có dữ liệu lịch sử định khoản để huấn luyện bộ gợi ý định khoản

## Giai đoạn 18 — Tạo bộ hóa đơn giả để thử nghiệm OCR/LLM

**Mục tiêu giai đoạn:** Có dữ liệu thử nghiệm cho PaddleOCR và Gemini Flash khi không lấy được hóa đơn thật từ hoadondientu và việc xin hóa đơn thật khó.

**Đã làm:**

- Viết `gen_invoices.py`: sinh hóa đơn GTGT dữ liệu giả (tên công ty, MST, địa chỉ đều giả, có dòng "DỮ LIỆU GIẢ - CHỈ DÙNG THỬ NGHIỆM") ở 3 kiểu trình bày; xuất PDF, ảnh PNG (khoảng 60% bị làm nhiễu: nghiêng, mờ, nhiễu hạt, bóng đổ, giảm độ phân giải để giống ảnh chụp điện thoại), XML mô phỏng cấu trúc hóa đơn điện tử (đơn giản hóa, chưa kiểm tra với XSD chính thức), và nhãn chuẩn `labels.json`/`labels.csv`
- Viết `score_fields.py`: so kết quả trích xuất với nhãn, tính tỷ lệ đúng từng trường, tách ảnh sạch và ảnh nhiễu
- Chạy thử 40 hóa đơn: tổng tiền khớp từng dòng, số tiền bằng chữ đúng, XML đọc được, script chấm điểm chạy đúng trên dự đoán giả

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** lấy mẫu thử ở đâu khi hoadondientu không lấy được
- **Đã chọn:** sinh hóa đơn giả có nhãn chuẩn làm bộ thử chính
- **Vì sao:** biết đáp án ngay, không lộ dữ liệu doanh nghiệp, gửi Gemini thoải mái, tạo được số lượng tùy ý. Đánh đổi: không phản ánh hết sự đa dạng của hóa đơn thật

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- Bộ giả chỉ có 3 kiểu trình bày, đẹp và đều hơn thực tế; kết quả đo trên bộ này cao hơn khi gặp hóa đơn thật, cần thử thêm vài hóa đơn thật đã che và ảnh biên lai MC-OCR (kiểm tra giấy phép trước)
- Chưa chạy PaddleOCR và Gemini Flash thật trên bộ giả, chưa có số liệu
- Cấu trúc XML là mô phỏng, cần đối chiếu với XML hóa đơn điện tử thật khi viết phần đọc XML
- Nếu báo cáo dùng số liệu từ bộ này phải ghi rõ là dữ liệu tổng hợp, mẫu nhỏ

## Giai đoạn 19 — Viết lại hướng dẫn cài đặt (README.md, SETUP.md) theo công nghệ đã chốt

**Mục tiêu giai đoạn:** Hai file hướng dẫn cho cả nhóm còn theo công nghệ cũ (Google Vision/Tesseract, GPT-4o-mini/Claude); cập nhật theo bảng công nghệ ở Giai đoạn 17 và thêm phần dữ liệu thử nghiệm.

**Đã làm:**

- `README.md`: bảng Tech Stack gộp nền tảng + AI; thêm thư mục `tools/`; thống nhất Python 3.12 và Node.js 20 LTS; thêm bước lấy Gemini API key (https://aistudio.google.com/apikey); thêm `alembic upgrade head` vào bước chạy backend; thêm cổng 5173 của frontend; mục Test data và Working with Git (nhánh main được bảo vệ, bắt buộc PR); sửa lỗi định dạng và bỏ các câu còn sót từ cuộc trò chuyện (VD: "matches your earlier error")
- `SETUP.md`: viết lại mục 3.1 AI Service gồm cài PaddlePaddle CPU (`paddlepaddle==3.2.0` từ chỉ mục của paddlepaddle.org.cn), `requirements.txt` (lõi) và `requirements-ml.txt` (scikit-learn, sentence-transformers), torch bản CPU, tải model lần đầu, kiểm tra PaddleOCR; đổi biến môi trường `GOOGLE_APPLICATION_CREDENTIALS`/`LLM_API_KEY` thành `GEMINI_API_KEY`, `LLM_MODEL` là tên model Flash hiện hành; thứ tự khởi động dùng nhiều terminal thay vì `&` (không chạy trên Windows); thêm mục 6 Test data (gen_invoices.py, score_fields.py, cài poppler theo từng hệ điều hành) và mục 7 Troubleshooting (gồm Bug 1 Python 3.14 và lỗi dùng `.env.example` cũ)
- Kiểm tra tài liệu chính thức: `pip install -U google-genai`, khóa lấy tại aistudio.google.com/apikey, biến `GEMINI_API_KEY`; PaddleOCR cài PaddlePaddle trước rồi `pip install paddleocr`

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** tách thư viện AI Service thành một hay hai file requirements
- **Đã chọn:** hai file: `requirements.txt` (FastAPI, Pillow, PaddleOCR, google-genai, RapidFuzz...) và `requirements-ml.txt` (scikit-learn, sentence-transformers)
- **Vì sao:** torch và bge-m3 rất nặng (vài GB); thành viên chỉ làm OCR/LLM không phải tải ngay
- **Vấn đề:** ngôn ngữ của README/SETUP
- **Đã chọn:** giữ tiếng Anh như bản cũ
- **Vì sao:** thống nhất với quyết định ở Giai đoạn 5 (README kỹ thuật tiếng Anh, báo cáo đồ án tiếng Việt); có thể dịch nếu nhóm muốn

**Bug gặp phải (nếu có) — đánh số theo thứ tự toàn dự án, không reset theo giai đoạn:**

- Không có bug mới ở giai đoạn này

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- Các file trong repo phải sửa cho khớp với hai file hướng dẫn: `ai-service/requirements.txt` (bỏ `google-cloud-vision`, `pytesseract`; thêm `paddleocr`, `google-genai`, `rapidfuzz`, `python-dotenv`), tạo `ai-service/requirements-ml.txt`, `.env.example` (bỏ `GOOGLE_APPLICATION_CREDENTIALS`, `LLM_API_KEY`; thêm `GEMINI_API_KEY`, `LLM_MODEL`), `ai-service/app/main.py` nếu có đọc biến cũ, và chép `gen_invoices.py`, `score_fields.py` vào `tools/`
- Chưa kiểm tra cài PaddlePaddle trên Python 3.12 và trên từng hệ điều hành (Windows, Mac, CachyOS) của 3 thành viên; mỗi người cần chạy bước kiểm tra trong SETUP mục 3.1 và báo lỗi
- Tên model Gemini Flash thay đổi theo thời gian; tài liệu mẫu hiện dùng `gemini-3.8-flash`, cần xem model nào có free tier trước khi điền `LLM_MODEL`
- Biến môi trường cho Google Sheets (service account) chưa thêm vì tính năng xuất Sheet chưa viết
- Migration Alembic cho 9 bảng chưa viết nên `alembic upgrade head` hiện chưa tạo đủ bảng

## Giai đoạn 20 — Thêm kiểu hóa đơn điện tử song ngữ vào bộ hóa đơn giả

**Mục tiêu giai đoạn:** Bộ hóa đơn giả ở Giai đoạn 18 còn đơn giản; cần thêm một kiểu có bố cục giống hóa đơn điện tử thường thấy trên cổng hoadondientu để thử PaddleOCR và Gemini sát thực tế hơn.

**Đã làm:**

- Thêm kiểu trình bày "portal" vào `gen_invoices.py` (cờ `--style portal` để chỉ tạo kiểu này; chế độ mặc định trộn 3 kiểu cũ và kiểu mới): nhãn song ngữ Việt-Anh, khung Mẫu số / Ký hiệu / Số, hàng đánh số cột (1, 2, 3, 4, 5, 6=4x5), dòng trống trong bảng, khung chữ ký số, dòng "Mã của cơ quan thuế" (chỉ với ký hiệu bắt đầu bằng C), mã tra cứu, dòng "Cần kiểm tra, đối chiếu khi lập, giao, nhận hóa đơn"
- Sửa nhãn: `mau_so` = 1 và `ky_hieu` dạng `C26TAA` (6 ký tự, C có mã cơ quan thuế, K không mã, năm 26, T/M, hai chữ cái) thay cho dạng gộp `1C26TAA` cũ; `score_fields.py` chấp nhận cả hai cách ghi; XML thêm thẻ `MCCQT` cho hóa đơn có mã
- Mọi chi tiết nhạy cảm đều giả và ghi rõ: tên công ty, MST, STK, ngân hàng "Mẫu Thử", chữ ký số ghi "CHỮ KÝ SỐ MẪU - KHÔNG CÓ GIÁ TRỊ", mã cơ quan thuế bắt đầu bằng "MẪU-THỬ-", website dùng tên miền `.example`, chìm chữ "MẪU THỬ NGHIỆM" và dòng "DỮ LIỆU GIẢ" ở chân trang
- Cập nhật SETUP.md mục 6 nói về `--style portal`

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** bố cục lấy theo đâu khi không vào được cổng hoadondientu
- **Đã chọn:** dựng theo bố cục chung của hóa đơn điện tử theo Thông tư 78 (nội dung bắt buộc và nhãn song ngữ phổ biến), không sao chép hóa đơn của doanh nghiệp nào
- **Vì sao:** không xem được bản gốc trên cổng; tài liệu tra cứu chỉ xác nhận nội dung bắt buộc (mẫu số, ký hiệu, số, người bán/mua, bảng hàng, thuế, tổng tiền, chữ ký số, mã cơ quan thuế) chứ không mô tả vị trí từng khối nên vị trí là ước lượng
- **Vấn đề:** có làm chữ ký số, mã cơ quan thuế, website trông như thật không
- **Đã chọn:** không, đều ghi rõ là mẫu/giả
- **Vì sao:** tránh tạo ra tài liệu có thể bị nhầm là hóa đơn thật; vẫn đủ để OCR/LLM học cách bỏ qua hoặc đọc các khối này

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- Bố cục là ước lượng, chưa đối chiếu với một hóa đơn thật; cần so với 1 đến 2 hóa đơn thật đã che (xin từ người quen) để chỉnh vị trí khối, cỡ chữ, tên cột
- Hóa đơn thật thường có mã QR; chưa vẽ mã QR
- Bộ giả vẫn chỉ có 4 kiểu trình bày; số liệu đo trên bộ này cao hơn khi gặp hóa đơn thật

## Giai đoạn 21 — Đề xuất phân công code cho 3 người

**Mục tiêu giai đoạn:** Chia việc code để cả 3 thành viên đều làm đầy đủ AI, backend, frontend và CSDL, không ai chỉ làm một tầng. Nhóm quyết định bỏ việc vẽ thêm hình sơ đồ để tập trung vào code.

**Đã làm:**

- Soạn `PHAN_CONG.md` (đặt vào `docs/`): chia theo nghiệp vụ thành 3 gói. Gói A: NV1 + NV2 + đăng nhập (bảng users, invoices, invoice_fields; PaddleOCR, Gemini, RapidFuzz). Gói B: NV3 + NV4 (bảng chart_of_accounts, journal_entries, item_categories, category_aliases; TF-IDF + Logistic Regression). Gói C: NV5 + NV6 + NV7 + khung giao diện (bảng purchase_orders, matching_results; bge-m3, Isolation Forest)
- Có danh sách việc từng gói, quy tắc tránh xung đột (hợp đồng API + mock, một migration cho 9 bảng, mỗi người một thư mục, nhánh + PR, review chéo A→B→C→A), lộ trình 8 tuần gợi ý, điều kiện hoàn thành
- Sau đó viết lại `PHAN_CONG.md` gán tên: Giáp Minh Hiển = gói A, Đới Gia Khánh = gói B, Trần Nam Dương = gói C; mỗi người có bảng việc chi tiết (A1–A11, B1–B9, C1–C9) kèm tuần làm, endpoint và sản phẩm bàn giao; danh sách endpoint chung làm hợp đồng; thứ tự làm sớm để không chờ nhau (A3 dữ liệu demo, A7 `llm.py`, C2 khung giao diện); review chéo Hiển→Khánh→Dương→Hiển

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** chia theo tầng (AI, backend, frontend) hay theo nghiệp vụ
- **Đã chọn:** theo nghiệp vụ (cắt dọc)
- **Vì sao:** chia theo tầng thì mỗi người chỉ làm một mảng và không ai làm trọn một tính năng; cắt dọc thì ai cũng có đủ AI, backend, frontend, CSDL để trình bày khi bảo vệ. Đánh đổi: cần thống nhất hợp đồng API sớm và dùng mock để không chờ nhau
- **Vấn đề:** ai nhận gói nào
- **Đã chọn:** Hiển = A, Khánh = B, Dương = C
- **Vì sao:** xếp theo vai trò hiện có trong báo cáo, không theo năng lực code: Hiển giữ repo, nền OCR/LLM và tổng hợp báo cáo, gói A là gói gốc các gói khác dựa vào; Khánh viết user story/use case nên quen màn hình hiệu chỉnh và định khoản; Dương vẽ Activity nên quen luồng duyệt. Đổi được nếu nhóm muốn
- **Vấn đề:** nhiều người tạo migration Alembic song song
- **Đã chọn:** một migration ban đầu cho cả 9 bảng, sau đó chỉ một PR migration tại một thời điểm
- **Vì sao:** tránh nhiều "head" trong Alembic và lệch CSDL giữa các máy

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- Nhóm họp xác nhận phân công theo tên, điều chỉnh nếu năng lực lệch nhau
- Điểm công sức (9, 10, 11 đv) là ước lượng thô; gói C nhiều phần ở mức Should/Could (PO, import, dashboard) nên làm Must (duyệt, xuất Sheet/Excel) trước
- Lộ trình 8 tuần là gợi ý, cần chỉnh theo hạn nộp thực tế
- Chưa có hợp đồng API chi tiết (đường dẫn, JSON vào/ra) và bản mock
- Bộ dữ liệu định khoản mẫu cho gói B chưa có; cần tạo vì chưa có lịch sử định khoản thật

## Giai đoạn 22 — Dựng lại thư mục dự án hoàn chỉnh (`ai-invoice-accounting.zip`)

**Mục tiêu giai đoạn:** Nhóm báo thư mục dự án cũ không giống bản đã thiết kế, nên dựng lại một thư mục đầy đủ khớp bảng công nghệ, ERD 9 bảng, tài liệu cài đặt và phân công đã chốt.

**Đã làm:**

- Dựng bộ khung: `docker-compose.yml` (MySQL 8.0, utf8mb4, healthcheck), `.env.example` (một `.env` duy nhất ở gốc), `.gitignore`
- Backend FastAPI: 9 model SQLAlchemy 2.0 theo từ điển dữ liệu, một migration Alembic `0001` tạo đủ 9 bảng, đăng nhập JWT + bcrypt thật (`/api/auth/login`, `/me`), hàm phân quyền `require_role` (chỉ KTT duyệt), `/api/health`, các endpoint hợp đồng của 3 gói trả dữ liệu mẫu có cờ `"mock": true`, script `seed_coa.py` (34 tài khoản TT133) và `seed_demo.py` (2 tài khoản demo, chỉ dùng khi dev), 5 test
- AI service FastAPI: `/health`, 8 endpoint mock (`/ocr`, `/extract`, `/normalize-vendor`, `/classify-gl`, `/classify-doc`, `/anomaly-score`, `/match-po`, `/summarize`), khung `llm.py`, 2 test
- Frontend React + Vite + Tailwind 3.4: đăng nhập, thanh điều hướng, chặn trang hàng chờ duyệt với KTV, 6 trang giữ chỗ gắn nhãn người phụ trách
- `tools/` (sinh và chấm hóa đơn giả), `data_test/` (12 hóa đơn giả mẫu), `docs/PHAN_CONG.md`, README.md và SETUP.md đã sửa
- Đã kiểm: `alembic upgrade/downgrade` trên SQLite, DDL MySQL biên dịch đúng (utf8mb4, InnoDB), pytest backend 5/5 và ai-service 2/2, `npm run build` thành công

**Quyết định kỹ thuật (nếu có):**

- **Vấn đề:** cách giao khung để 3 người làm song song
- **Đã chọn:** endpoint mock có cờ `"mock": true`, người phụ trách làm xong thì chuyển sang router riêng và xóa khỏi `mock_contract.py`
- **Vì sao:** frontend dùng được ngay từ tuần 1, không ai chờ ai
- **Vấn đề:** SETUP.md ghi sai cơ chế utf8mb4 (`MYSQL_CHARACTER_SET`)
- **Đã chọn:** sửa thành cờ `--character-set-server` / `--collation-server` trong `command` của docker-compose
- **Vì sao:** biến môi trường đó không có trong image MySQL; cờ khởi động mới là cơ chế thật

**Việc còn tồn đọng từ giai đoạn này (nếu có):**

- Thư mục này dựng lại từ tài liệu, không phải bản repo cũ của nhóm: phải so với lịch sử Git trước khi gộp, không ghi đè code đã có
- Chưa chạy thử với MySQL thật (môi trường dựng không có Docker); chỉ kiểm DDL và migration bằng SQLite
- `seed` tài khoản TT133 cần đối chiếu lại với thông tư
- `LLM_MODEL` (gemini-3.8-flash) phải kiểm tra lại model Flash miễn phí hiện hành
- Cài PaddlePaddle/PaddleOCR chưa thử trên mọi hệ điều hành; `requirements-ml.txt` chưa cài thử
- Gói `mock` còn lại là việc của A, B, C theo `docs/PHAN_CONG.md`

# Kiến thức đã áp dụng

- [[]]