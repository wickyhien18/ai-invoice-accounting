# Phần báo cáo — Gói A: tiếp nhận, bóc tách bằng AI và kiểm tra sơ bộ

Người viết: Giáp Minh Hiển. Phạm vi: NV1 (tiếp nhận và bóc tách bằng AI) và NV2 (kiểm tra sơ bộ, đăng nhập, phân quyền).
Số liệu độ chính xác dưới đây đo trên **12 hóa đơn giả (mẫu nhỏ)**, không suy ra được độ chính xác trên hóa đơn thật.

## 1. Kiến trúc

```
Trình duyệt ──► Backend FastAPI ──► ai-service FastAPI
 (React)         │  /api/invoices      │  /ocr   /extract   /normalize-vendor
                 │  /api/auth          │
                 ▼                     ▼
              MySQL                PaddleOCR (cục bộ) · Gemini Flash · RapidFuzz
```

Luồng một hóa đơn:

1. Người dùng tải file lên `POST /api/invoices`. Backend kiểm tra đuôi file, chữ ký đầu file và dung lượng (≤ 10 MB), lưu file, tạo bản ghi `invoices` ở trạng thái `dang_xu_ly`.
2. **XML:** đọc trực tiếp (`xml_parser.py`), không qua OCR, độ tin cậy 100. **PDF/ảnh:** backend chạy nền, gọi `POST /extract` của ai-service.
3. ai-service: PDF có lớp chữ thì lấy chữ trực tiếp; ảnh và PDF scan được tiền xử lý rồi qua PaddleOCR. Các ô chữ được gom thành dòng theo tọa độ. Văn bản đưa cho Gemini (đã che MST, số tài khoản, số điện thoại, email) để trả JSON 9 trường; song song chạy bộ quy tắc regex để đối chiếu.
4. Mỗi trường được chấm độ tin cậy 0–100 và lưu vào `invoice_fields.extracted_value` / `confidence_score`. Hóa đơn chuyển sang `cho_xac_nhan`, hoặc `loi_xu_ly` nếu lỗi (có nút xử lý lại).
5. Kiểm tra sơ bộ `POST /api/invoices/{id}/check`: MST đúng định dạng, trước thuế + thuế = tổng thanh toán và thuế suất khớp tiền thuế (lệch tối đa 1 đồng), không trùng ký hiệu + số + MST; gợi ý tên người bán chuẩn bằng RapidFuzz.

## 2. Cài đặt chính

| Thành phần | Tệp | Ghi chú |
|---|---|---|
| Đăng nhập JWT, bcrypt, 2 vai trò | `backend/app/security.py`, `routers/auth.py` | `require_role("KTT")` dùng chung |
| API hóa đơn | `backend/app/routers/invoices.py` | file gốc chỉ mở khi có token |
| Đọc XML | `backend/app/services/xml_parser.py` | `defusedxml`, bỏ namespace, nhiều thuế suất thì để trống và cảnh báo |
| Kiểm tra sơ bộ | `backend/app/services/checks.py` | thuần hàm, có test |
| OCR | `ai-service/app/services/ocr.py`, `preprocess.py` | xoay thẳng bằng phương sai ngang, phóng to, giảm nhiễu, tăng tương phản |
| LLM dùng chung | `ai-service/app/llm.py` | thử lại, phân biệt hết hạn mức và sai khóa |
| Trích xuất + độ tin cậy | `ai-service/app/services/extractor.py` | công thức cộng trừ điểm ghi trong đầu tệp |
| Che dữ liệu nhạy cảm | `ai-service/app/services/masking.py` | che MST/STK/SĐT/email, không che tên công ty |
| Chuẩn hóa tên người bán | `ai-service/app/services/vendor.py` | bỏ dấu, bỏ dạng pháp lý, `token_sort_ratio` ≥ 88 |
| Giao diện | `frontend/src/pages/invoices/` | tải nhiều file, danh sách có lọc, chi tiết, kiểm tra |

**Độ tin cậy.** Không lấy thẳng số LLM tự báo (LLM chấm điểm thường lệch). Điểm gốc 50, cộng/trừ theo: giá trị có trong văn bản OCR (+20/−25), quy tắc regex đọc cùng (+15/−10), định dạng hợp lệ (+5/−20), ba trường tiền khớp phép cộng (+10/−20), độ tin cậy OCR của dòng chứa giá trị, và mức chắc chắn LLM tự báo (trọng số nhỏ). Một giá trị LLM bịa ra, không có trong văn bản, sẽ xuống dưới 70 (ô đỏ) dù LLM báo 99. Có test cho trường hợp này.

**Rơi về quy tắc.** Khi Gemini không dùng được (không có khóa, hết hạn mức 429, máy chủ lỗi), `/extract` vẫn trả kết quả từ regex kèm cảnh báo, nên hóa đơn không bị kẹt.

## 3. Kết quả thử nghiệm

### 3.1. Đã đo (môi trường dựng, không có PaddleOCR và Gemini)

| Thử nghiệm | Kết quả |
|---|---|
| Đọc XML trực tiếp, 12 file `data_test/xml` | 12/12 hóa đơn khớp nhãn ở số hóa đơn, MST, tên, tiền trước thuế, thuế suất, tổng thanh toán |
| Quy tắc regex trên 12 PDF có lớp chữ (không OCR, không LLM) | 108/108 ô đúng (9 trường × 12). Đây là trường hợp dễ nhất, **không phản ánh ảnh chụp** |
| Hiệu chuẩn độ tin cậy trên 12 PDF đó | xanh ≥ 90: 96/96 đúng; vàng: 12/12 đúng (vàng toàn là tên người bán); đỏ: 0 ô |
| Xoay thẳng ảnh | ảnh nghiêng 3° được ước lượng lại với sai số ≤ 1° |
| Test tự động | backend 21/21, ai-service 21/21, `npm run build` thành công |
| Chạy thật qua HTTP | tải PDF và XML qua backend → ai-service → CSDL; phát hiện hóa đơn trùng; file gốc trả 401 khi không có token |

### 3.2. Chưa đo — cần chạy trên máy có PaddleOCR và khóa Gemini

Môi trường dựng chỉ cho tải gói pip, không tải được mô hình PaddleOCR và không có khóa Gemini, nên **chưa có số liệu đọc ảnh**. Điền bảng sau bằng `tools/eval_extraction.py` (mỗi lệnh ghi `eval_out/<tên>/report.md`):

| Cấu hình | Lệnh | Tổng ô đúng | Ảnh sạch | Ảnh nhiễu |
|---|---|---|---|---|
| PaddleOCR + regex, không tiền xử lý | `--source images --no-llm --no-preprocess` | _chưa đo_ | | |
| PaddleOCR + regex, có tiền xử lý | `--source images --no-llm` | _chưa đo_ | | |
| PaddleOCR + Gemini, có tiền xử lý | `--source images` | _chưa đo_ | | |
| PDF ép qua PaddleOCR | `--source pdf_ocr` | _chưa đo_ | | |

Cặp đầu cho biết tiền xử lý ảnh có ích không; cặp giữa cho biết Gemini cải thiện bao nhiêu so với regex. Nếu có thể, thử thêm vài hóa đơn thật đã che MST và tên rồi chấm tay.

## 4. Hạn chế đã biết

- Dữ liệu là hóa đơn giả với ba mẫu trình bày đơn giản; mẫu thật đa dạng hơn nhiều.
- MST chỉ kiểm tra định dạng, không kiểm tra số kiểm tra và không tra cứu cơ quan thuế (MST giả là số ngẫu nhiên; nhóm đã chốt không kết nối hoadondientu).
- Hóa đơn nhiều mức thuế suất: XML để trống thuế suất và cảnh báo; luồng ảnh chưa xử lý riêng.
- Gemini bản miễn phí có thể dùng dữ liệu gửi lên để cải thiện sản phẩm; MST, số tài khoản, số điện thoại, email được che nhưng **tên công ty không che**, nên chỉ gửi hóa đơn giả hoặc đã che tên.
- Các ngưỡng cộng trừ điểm tin cậy chọn tay; cần xem bảng hiệu chuẩn sau khi có số liệu OCR thật.
- Hóa đơn nhiều trang: PDF scan được OCR từng trang và ghép dòng, chưa tách riêng bảng dòng hàng.
