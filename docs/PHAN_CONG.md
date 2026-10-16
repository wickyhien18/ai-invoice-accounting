# Phân công code — ai-invoice-accounting (nhóm 15)

> Bản đề xuất để cả nhóm họp thống nhất. Nếu ai muốn đổi gói thì đổi nguyên gói cho nhau, đừng chia nhỏ lại.

## 1. Nguyên tắc

Chia theo **nghiệp vụ** (NV1–NV7), không chia theo tầng. Mỗi người sở hữu một gói nghiệp vụ và tự làm đủ 4 lớp cho gói đó: AI/ML (ai-service), backend (FastAPI), frontend (React), CSDL (model và migration). Mỗi người tự viết test, tự đo kết quả phần AI của mình và tự viết phần báo cáo về phần code của mình.

## 2. Ai làm gì (tóm tắt)

| Thành viên | Gói | Nghiệp vụ | Bảng CSDL | AI/ML |
|---|---|---|---|---|
| **Giáp Minh Hiển** | A — Tiếp nhận và bóc tách | NV1 Tiếp nhận và bóc tách bằng AI, NV2 Kiểm tra sơ bộ, đăng nhập và phân quyền | users, invoices, invoice_fields | PaddleOCR, Gemini Flash, RapidFuzz |
| **Đới Gia Khánh** | B — Hiệu chỉnh và định khoản | NV3 Đối chiếu song song và hiệu chỉnh, NV4 Gợi ý định khoản Nợ/Có | chart_of_accounts, journal_entries, item_categories, category_aliases | TF-IDF + Logistic Regression, phân loại tài liệu |
| **Trần Nam Dương** | C — Duyệt, đối chiếu đơn hàng, xuất báo cáo | NV5 Đối chiếu đơn đặt hàng, NV6 Phê duyệt hai cấp, NV7 Xuất bảng kê và báo cáo, khung giao diện chung | purchase_orders, matching_results | Isolation Forest, bge-m3, tóm tắt báo cáo (nếu kịp) |

Lý do xếp như trên (theo vai trò hiện có trong báo cáo, không theo năng lực code, nên đổi được): Hiển giữ repo, nền công nghệ OCR/LLM và tổng hợp báo cáo, nên nhận gói A là gói gốc mà hai gói kia dựa vào. Khánh viết user story và use case nên quen với màn hình hiệu chỉnh và định khoản. Dương vẽ Activity Diagram nên quen với luồng duyệt và các bước trạng thái.

## 3. Việc chi tiết từng người

Cột "Tuần" là gợi ý, tuần 1 là tuần bắt đầu code. Các việc có chữ (Could) chỉ làm khi còn thời gian.

### 3.1. Giáp Minh Hiển — Gói A

| Mã | Tuần | Việc | Bàn giao |
|---|---|---|---|
| A1 | 1 | Viết model và migration cho users, invoices (file_path, file_type, deduct_group, status, export_status...), invoice_fields (extracted_value, final_value, confidence). **Gộp migration đầu tiên của cả 9 bảng** từ phần của 3 người | `alembic upgrade head` tạo đủ 9 bảng trên máy cả nhóm |
| A2 | 1–2 | Đăng nhập JWT, mã hóa bcrypt, hai vai trò (kế toán viên, kế toán trưởng), hàm kiểm tra quyền dùng chung; tạo sẵn 2 tài khoản demo | `POST /api/auth/login`, `GET /api/auth/me` |
| A3 | 2 | Script nạp dữ liệu demo: đọc `data_test/labels.json` rồi tạo hóa đơn và trường trong CSDL, để Khánh và Dương làm việc mà không chờ OCR | `python scripts/seed_demo.py` |
| A4 | 2 | API tải hóa đơn (PDF, ảnh, XML), lưu file, chỉ người đã đăng nhập mới mở được file, danh sách có lọc, chi tiết | `POST /api/invoices`, `GET /api/invoices`, `GET /api/invoices/{id}`, `GET /api/invoices/{id}/file` |
| A5 | 2–3 | Đọc trực tiếp XML hóa đơn điện tử, không qua OCR | hàm parser và test với `data_test/xml` |
| A6 | 2–3 | Endpoint OCR: PaddleOCR tiếng Việt, tiền xử lý ảnh bằng Pillow | `POST /ocr` |
| A7 | 3–4 | Endpoint trích xuất: gọi Gemini Flash, ép trả JSON các trường trọng yếu kèm độ tin cậy, xử lý lỗi hết hạn mức, che dữ liệu nhạy cảm khi cần. Viết thành module gọi LLM dùng chung `ai-service/app/llm.py` để Khánh cũng dùng | `POST /extract`, `llm.py` |
| A8 | 4 | Kiểm tra sơ bộ: định dạng MST, tổng tiền khớp tổng dòng cộng thuế, trùng số hóa đơn/ký hiệu/MST; chuẩn hóa tên người bán bằng RapidFuzz | `POST /api/invoices/{id}/check`, `POST /normalize-vendor` |
| A9 | 3–4 | Frontend: trang đăng nhập, trang tải hóa đơn (kéo thả, nhiều file), danh sách hóa đơn và trạng thái | 3 trang chạy được |
| A10 | 6–7 | Đánh giá: chạy PaddleOCR và Gemini trên bộ hóa đơn giả, chấm bằng `tools/score_fields.py`, lập bảng độ chính xác từng trường (ảnh sạch, ảnh nhiễu); thử thêm vài hóa đơn thật đã che nếu xin được | bảng kết quả và phần báo cáo OCR/LLM |
| A11 | suốt | Giữ README, SETUP, nhật ký `AI-Invoice-Scan.md`; tổng hợp và gộp báo cáo | tài liệu luôn đúng với code |

### 3.2. Đới Gia Khánh — Gói B

| Mã | Tuần | Việc | Bàn giao |
|---|---|---|---|
| B1 | 1 | Model và migration cho chart_of_accounts, journal_entries (số tiền DECIMAL(18,2), hai khóa ngoại debit_account và credit_account), item_categories, category_aliases; nạp danh mục tài khoản theo TT133 | file model, seed trong `database/` |
| B2 | 2 | API đọc và sửa trường: giữ extracted_value, ghi final_value khi kế toán viên sửa; quy tắc màu độ tin cậy (xanh ≥ 90, vàng 70 đến dưới 90, đỏ < 70) | `GET /api/invoices/{id}/fields`, `PATCH /api/invoices/{id}/fields/{field_id}` |
| B3 | 2–3 | Frontend màn hình đối chiếu chia đôi: ảnh hoặc PDF bên trái, trường bên phải, tô màu theo độ tin cậy, sửa trực tiếp; trạng thái chia màn hình lưu ở trình duyệt, không lưu CSDL | trang đối chiếu |
| B4 | 2–3 | Tạo bộ dữ liệu định khoản mẫu bằng script (vài trăm dòng; đặc trưng: người bán, thuế suất, tổng tiền, lịch sử định khoản; nhãn: tài khoản Nợ và Có theo TT133) | `tools/gen_gl_data.py` và file dữ liệu |
| B5 | 3–4 | Huấn luyện TF-IDF + Logistic Regression, chia tập huấn luyện/kiểm thử riêng, lưu mô hình, đo độ chính xác | `POST /classify-gl` (trả Nợ, Có, xác suất), mô hình và số liệu |
| B6 | 4 | API gợi ý và lưu bút toán; với người bán mới (chưa có lịch sử) gọi Gemini qua `llm.py` của Hiển và ghi rõ nguồn gợi ý | `POST /api/invoices/{id}/suggest-entries`, `PUT /api/invoices/{id}/journal-entries` |
| B7 | 4–5 | Frontend: màn hình định khoản (hiện gợi ý, sửa Nợ/Có), quản lý danh mục tài khoản và loại khoản | 2 trang |
| B8 | 5 | Endpoint phân loại loại tài liệu đầu vào (Logistic Regression) (Could) | `POST /classify-doc` |
| B9 | 6–7 | Đánh giá độ chính xác gợi ý định khoản trên tập kiểm thử và phần báo cáo của mình | bảng kết quả, phần báo cáo |

### 3.3. Trần Nam Dương — Gói C

| Mã | Tuần | Việc | Bàn giao |
|---|---|---|---|
| C1 | 1 | Model và migration cho purchase_orders, matching_results (có amount_difference, match_status) | file model |
| C2 | 1–2 | Khung giao diện chung: Vite, React, Tailwind, router, hàm gọi API, chặn trang theo vai trò, layout và thanh menu. Giai đoạn đầu dùng token giả cho đến khi đăng nhập của Hiển xong. **Làm sớm vì Hiển và Khánh gắn trang vào khung này** | khung chạy được ở cổng 5173 |
| C3 | 2–3 | Luồng trạng thái hóa đơn: gửi duyệt, duyệt, từ chối kèm lý do (status, reject_reason, approved_by, approved_at), chỉ kế toán trưởng được duyệt, hàng chờ duyệt | `POST /api/invoices/{id}/submit`, `/approve`, `/reject`, `GET /api/approvals`, trang hàng chờ |
| C4 | 3–4 | Xuất bảng kê mẫu 01-2/GTGT ra Excel (openpyxl) và Google Sheet (Google Sheets API), tách `export_status` khỏi `status` để xuất lại không bị ghi trùng | `POST /api/exports/sheet`, file Excel mẫu |
| C5 | 4–5 | Cảnh báo bất thường và trùng bằng Isolation Forest (huấn luyện từ bộ hóa đơn giả), hiển thị cảnh báo ở hàng chờ duyệt | `POST /anomaly-score`, cảnh báo trên giao diện |
| C6 | 4–5 | Nhập PO bằng form, danh sách PO, API | `POST/GET /api/purchase-orders`, trang PO |
| C7 | 5–6 | Đối chiếu PO: bge-m3 để ghép hóa đơn với PO, tính chênh lệch số tiền, ghi matching_results; hóa đơn không có PO thì không có dòng đối chiếu | `POST /match-po`, `POST /api/invoices/{id}/match-po`, trang đối chiếu PO |
| C8 | 6 | (Could) Nhập PO từ Excel/CSV, dashboard chi tiêu theo tháng và nhà cung cấp, tóm tắt báo cáo bằng Gemini | `POST /api/purchase-orders/import`, `GET /api/reports/spending`, `POST /summarize` |
| C9 | 6–7 | Đánh giá Isolation Forest và đối chiếu PO, phần báo cáo của mình | bảng kết quả, phần báo cáo |

## 4. Ba người cần thống nhất với nhau (tuần 1)

- **Danh sách endpoint ở trên** là hợp đồng. Mỗi người làm sẵn bản giả trả dữ liệu cố định cho endpoint của mình trong tuần 1 để người khác gọi được ngay.
- **Hiển làm A3 sớm** (dữ liệu demo trong CSDL), vì Khánh và Dương cần hóa đơn có trường để làm màn hình và luồng duyệt.
- **Hiển làm A7 (`llm.py`) sớm** để Khánh dùng chung cho gợi ý người bán mới. Trong lúc chờ, Khánh dùng bản giả.
- **Dương làm C2 (khung giao diện) sớm** để Hiển và Khánh gắn trang vào.
- **Migration:** mỗi người viết model cụm bảng của mình (A1, B1, C1), Hiển gộp thành một migration đầu tiên. Sau đó chỉ một PR migration tại một thời điểm và phải `git pull` main trước khi tạo revision mới.

## 5. Quy tắc làm việc chung

1. Nhánh riêng cho mỗi việc (ví dụ `feature/a4-upload`), PR nhỏ, `main` không push trực tiếp.
2. **Review chéo:** Hiển review Khánh, Khánh review Dương, Dương review Hiển.
3. Mỗi người một thư mục: `backend/app/routers/<mã nghiệp vụ>_*.py`, `ai-service/app/routers/<tên endpoint>.py`, `frontend/src/pages/<tên trang>/`. File dùng chung (đăng ký router, route chính) chỉ thêm một dòng mỗi lần.
4. Họp ghép nối mỗi tuần 15–30 phút, chạy thử chuỗi tải hóa đơn đến xuất báo cáo bằng bộ hóa đơn giả.
5. Không commit `.env`, API key, hoặc ảnh hóa đơn thật.

## 6. Báo cáo

Mỗi người viết phần báo cáo về phần code của mình (kiến trúc, cài đặt, kết quả thử nghiệm): Hiển về OCR/LLM và kiểm tra sơ bộ, Khánh về định khoản, Dương về duyệt, đối chiếu PO và xuất báo cáo. Hiển tổng hợp và gộp vào file báo cáo. Số liệu độ chính xác phải ghi rõ là dữ liệu giả, mẫu nhỏ.

## 7. Lộ trình gợi ý (chỉnh theo hạn nộp)

| Tuần | Việc chính |
|---|---|
| 1 | A1, B1, C1 (model, migration chung), C2 khung giao diện, mock endpoint, bắt đầu A2 |
| 2–3 | Các việc A2–A6, B2–B5, C3–C4 |
| 4–5 | A7–A9, B6–B8, C5–C7; ghép nối đầu tiên |
| 6 | Ghép nối cả chuỗi, C8 nếu kịp, sửa lỗi |
| 7 | Đánh giá (A10, B9, C9), viết báo cáo |
| 8 | Chuẩn bị demo và bảo vệ |

## 8. Điều kiện hoàn thành của mỗi người

- Có luồng chạy được từ giao diện qua backend và ai-service xuống CSDL
- Có test cho logic chính
- Có số liệu đánh giá phần AI của mình
- Trình bày được toàn bộ phần của mình khi bảo vệ, từ giao diện đến mô hình
