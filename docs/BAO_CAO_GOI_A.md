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

### 3.2. Đọc ảnh PNG (PaddleOCR) — đã đo trên 12 ảnh giả

Đo bằng `tools/eval_extraction.py` trên máy nhóm (PaddleOCR 3.x, Gemini `gemini-3.8-flash`), 12 ảnh PNG (6 sạch, 6 nhiễu), 9 trường mỗi ảnh = 108 ô. Đây là **mẫu nhỏ, hóa đơn giả**, không suy ra độ chính xác trên hóa đơn thật.

| Cấu hình | Tổng ô đúng | Ảnh sạch | Ảnh nhiễu | Thời gian/ảnh |
|---|---|---|---|---|
| PaddleOCR + regex (có tiền xử lý) | 94/108 (87%) | | | 14,2 s |
| PaddleOCR + Gemini (có tiền xử lý) | 97/108 (90%) | | | 19,0 s |
| PaddleOCR + regex, không tiền xử lý | _chưa đo_ | | | |
| PDF ép qua PaddleOCR | _chưa đo_ | | | |

Độ chính xác theo trường (Gemini / regex): số ký hiệu 92% / 92%; số hóa đơn 92% / 83%; ngày lập 100% / 100%; MST 100% / 92%; tiền trước thuế 92% / 92%; thuế suất 100% / 92%; tiền thuế 100% / 100%; tổng thanh toán 92% / 92%; **tên người bán chỉ 42% ở cả hai** (5/12).

Hiệu chuẩn độ tin cậy (ô xanh/vàng/đỏ có đúng thật không):

| Dải | Regex: số ô, tỉ lệ đúng | Gemini: số ô, tỉ lệ đúng |
|---|---|---|
| Xanh ≥ 90 | 89 ô, 97% | 94 ô, 94% |
| Vàng 70–90 | 15 ô, 53% | 13 ô, 69% |
| Đỏ < 70 | 4 ô, 0% | 1 ô, 0% |

Nhận xét:
- Gemini chỉ hơn regex 3 điểm phần trăm (97 so với 94 ô đúng). Phần lớn cải thiện ở MST, thuế suất, số hóa đơn. Gemini chỉ nhận chữ do OCR đọc ra nên không sửa được lỗi OCR đã sai ký tự.
- Ô đỏ đều sai (0% đúng) nên cảnh báo màu có tác dụng: kế toán biết phải kiểm tra. Ô xanh vẫn sai 3–6%, nên **không được bỏ bước người duyệt**.
- Tên người bán là điểm yếu lớn nhất (5/12). Xem từng ảnh thì lỗi nằm ở OCR: nó bỏ hẳn các chữ có dấu phức tạp (ví dụ "Văn phòng phm Mu Th Cường" thay vì "phẩm Mẫu Thử"; "Dch vu" thay vì "Dịch vụ"), hoặc đọc sai dấu. Ô này được chấm là đúng chỉ khi tên khớp sau khi bỏ dấu, nên các tên bị mất chữ đều tính là sai. Gemini không khôi phục được vì chỉ thấy chữ OCR. Cách khắc phục đã có: chuẩn hóa theo danh sách nhà cung cấp đã biết bằng RapidFuzz. Thử riêng trên 12 tên OCR sai này với danh sách 6 nhà cung cấp, tên chuẩn hóa về đúng 12/12 (điểm khớp 90–100). Lưu ý danh sách chỉ có 6 tên và rất khác nhau, nên đây là điều kiện dễ; với nhà cung cấp mới chưa có trong danh sách thì kế toán vẫn phải sửa tay.
- Thời gian 14–19 giây/ảnh trên CPU, chủ yếu do OCR.
- Hai lần Gemini trả 503 (quá tải) khi chạy; hệ thống thử lại và vẫn xử lý xong.
- Cơ chế tự sửa bằng phép tính (thuế = trước thuế × thuế suất; tổng = trước thuế + thuế) được đánh dấu "computed", độ tin cậy cố định 72 (vàng).

## 4. Hạn chế đã biết

- Dữ liệu là hóa đơn giả với ba mẫu trình bày đơn giản; mẫu thật đa dạng hơn nhiều.
- MST chỉ kiểm tra định dạng, không kiểm tra số kiểm tra và không tra cứu cơ quan thuế (MST giả là số ngẫu nhiên; nhóm đã chốt không kết nối hoadondientu).
- Hóa đơn nhiều mức thuế suất: XML để trống thuế suất và cảnh báo; luồng ảnh chưa xử lý riêng.
- Gemini bản miễn phí có thể dùng dữ liệu gửi lên để cải thiện sản phẩm; MST, số tài khoản, số điện thoại, email được che nhưng **tên công ty không che**, nên chỉ gửi hóa đơn giả hoặc đã che tên.
- Các ngưỡng cộng trừ điểm tin cậy chọn tay; cần xem bảng hiệu chuẩn sau khi có số liệu OCR thật.
- Hóa đơn nhiều trang: PDF scan được OCR từng trang và ghép dòng, chưa tách riêng bảng dòng hàng.

## 5. Lỗi gặp phải và cách sửa

| # | Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|---|
| 1 | Ảnh PNG/JPG chỉ đọc được ngày lập; PDF và XML đọc tốt | Quy tắc regex viết theo văn bản PDF sạch, không chịu được chữ OCR bị mất dấu, mất dấu `:`, nhầm `O/0`, `l/1` | Viết lại quy tắc trong `rules.py`: so khớp nhãn trên bản đã bỏ dấu, dấu `:` tùy chọn, sửa nhầm ký tự trong số tiền; thêm test với văn bản bị làm hỏng |
| 2 | Số hóa đơn đọc thành `0000001` | Regex bắt nhầm "Mẫu số (Form): 1" | Thêm điều kiện loại trừ "Mẫu số", chọn ứng viên có nhiều chữ số nhất |
| 3 | Ảnh mãi ở trạng thái "đang xử lý" khi không tải được mô hình PaddleOCR | Mỗi yêu cầu đều thử tải lại mô hình và chờ hết thời gian | Ghi nhớ lỗi tải trong 5 phút, khởi động nóng mô hình khi bật server, thêm `ocr_ready` ở `/health`, thêm trạng thái `loi_xu_ly` |
| 4 | Sau khi sửa quy tắc, tiền thuế đọc thành `11717001717002` | Mẫu số tiền cho phép khoảng trắng nên dính số của hai dòng | Bỏ khoảng trắng khỏi mẫu số |
| 5 | Dòng hàng "Tiền thuê phòng họp" bị nhận làm tiền thuế VAT | Sau khi bỏ dấu, "thuê" và "thuế" giống nhau | Chỉ nhận "Tiền thuế" khi theo sau là GTGT/VAT hoặc `:`; thêm test riêng |
| 6 | Mất số hóa đơn khi OCR làm mất dấu `:` | Mẫu yêu cầu có dấu `:` | Thêm mẫu "Số" kèm 6–8 chữ số không cần `:` và mẫu "(No.)" |
| 7 | Gemini không chạy, hệ thống âm thầm dùng regex | `.env` đặt `LLM_MODEL=gpt-4o-mini` (tên model OpenAI cho khóa Gemini); sau đó `gemini-2.5-flash` bị Google ngừng cấp cho tài khoản mới (lỗi 404) | Đổi mặc định và `.env` sang `gemini-3.8-flash`; khi Gemini lỗi, hệ thống dùng regex và ghi lý do vào danh sách cảnh báo của kết quả |
| 8 | Ảnh thật: ngày, thuế suất, tiền thuế, tổng bị bỏ sót; tiền đọc sai 1 chữ số (310.548 thay vì 310.568; 4.192.660 thay vì 4.192.668) | OCR đọc "Ngày" thành "Ngby", "Tiền thuế" thành "Tidn thué"; quy tắc quá cứng | Dùng nhãn tiếng Anh trong ngoặc làm điểm tựa, đọc ngày theo "…tháng…năm…", so khớp mờ bằng RapidFuzz; tự sửa số tiền lệch tối đa 2 chữ số bằng phép tính (thuế = trước thuế × thuế suất; tổng = trước thuế + thuế), đánh dấu "computed", độ tin cậy cố định 72 (vàng) kèm cảnh báo |
| 9 | Ký hiệu hóa đơn đọc thành `C26M8S` (đúng là `C26MBF`) | OCR đọc sai ký tự, Gemini chỉ thấy chữ OCR | Không sửa tự động vì đoán sai sẽ ra một ký hiệu hợp lệ nhưng sai; ô được tô đỏ (52,8) để kế toán kiểm tra |
| 10 | Tên người bán sai ở 7/12 ảnh | OCR mất hoặc sai chữ có dấu | Chuẩn hóa theo danh sách nhà cung cấp bằng RapidFuzz (xem 3.2); chưa giải quyết được với nhà cung cấp mới |
| 11 | Gemini trả 503 "quá tải" | Máy chủ Gemini bận | Thử lại tối đa 3 lần; nếu vẫn lỗi thì dùng quy tắc, kết quả vẫn được trả |
| 12 | Công cụ debug/đánh giá đòi tự tạo venv ở thư mục gốc | Script dùng Python hệ thống | Thêm `tools/_venv.py` tự chạy lại bằng Python của `ai-service/venv` |
| 13 | Script đánh giá báo "Connection refused" | Chưa bật ai-service trước khi chạy | Ghi rõ trong hướng dẫn: bật ai-service rồi mới chạy; dừng server bằng `Ctrl+C`, không dùng `Ctrl+Z` (chỉ tạm dừng, cổng vẫn bị chiếm) |
| 14 | Một số thư viện được cài mà không thông báo | Danh sách phụ thuộc chưa được rà soát | Rà lại trên môi trường sạch và liệt kê đầy đủ trong `requirements.txt` và `SETUP.md` |
