# Phần báo cáo — Gói C: Duyệt, đối chiếu đơn hàng, xuất báo cáo

Người viết: Trần Nam Dương. Phạm vi: NV5 (Đối chiếu đơn đặt hàng), NV6 (Phê duyệt hai cấp), NV7 (Xuất bảng kê và báo cáo, khung giao diện chung).
Số liệu độ chính xác dưới đây đo trên **dữ liệu hóa đơn và PO giả (mẫu nhỏ)**, không suy ra được độ chính xác trên dữ liệu thật.

## 1. Kiến trúc

```text
Trình duyệt ──► Backend FastAPI ──► ai-service FastAPI
 (React Vite)    │  /api/approvals     │  /anomaly-score (Isolation Forest)
 Khung Layout    │  /api/purchase-...  │  /match-po (bge-m3)
                 │  /api/exports       │
                 ▼                     ▼
              MySQL                Mô hình cục bộ (scikit-learn, HuggingFace)
```

Luồng nghiệp vụ xử lý:

1. **Khung giao diện (Layout):** Mọi tương tác của người dùng đi qua khung Frontend (Vite + React + Tailwind) có gắn định tuyến bảo vệ (`ProtectedRoute`). Dựa vào token từ Gói A, giao diện phân quyền hiển thị (Kế toán viên chỉ xem/nhập PO, Kế toán trưởng được duyệt hóa đơn).
2. **Luồng phê duyệt (NV6):** Hóa đơn sau khi qua đối chiếu và hiệu chỉnh (Gói B) sẽ ở trạng thái `cho_duyet`. Kế toán trưởng gọi `POST /api/invoices/{id}/approve` (chuyển sang `da_duyet`) hoặc `/reject` (trả về `tu_choi` kèm lý do).
3. **Cảnh báo bất thường (NV5):** Tại hàng chờ duyệt, Backend gọi sang `POST /anomaly-score` của ai-service. AI dùng thuật toán Isolation Forest để phát hiện bất thường dựa trên lịch sử chi tiêu, tô sáng cảnh báo để Kế toán trưởng lưu ý trước khi bấm duyệt.
4. **Đối chiếu PO (NV5):** Người dùng nhập hoặc tải lên Đơn đặt hàng (Purchase Order - PO). Khi cần đối chiếu, hệ thống gọi `POST /match-po` sang ai-service, sử dụng mô hình nhúng `bge-m3` để so khớp ngữ nghĩa tên mặt hàng/nhà cung cấp giữa Invoice và PO, từ đó tính chênh lệch tổng tiền.
5. **Xuất báo cáo (NV7):** Kế toán viên chọn danh sách hóa đơn `da_duyet` để xuất bảng kê 01-2/GTGT. Nút "Xuất Excel" gọi Backend (`openpyxl`) tạo file `.xlsx` hoặc đẩy thẳng lên Google Sheets qua API. Hóa đơn đã xuất được đánh dấu `export_status = exported` để tránh xuất trùng.

## 2. Cài đặt chính

| Thành phần | Tệp | Ghi chú |
|---|---|---|
| Khung giao diện (Layout, Router) | `frontend/src/App.jsx`, `components/Layout/` | Thanh menu chung, chặn trang bằng `require_role`, quản lý trạng thái token |
| API Luồng duyệt | `backend/app/routers/approvals.py` | Kiểm tra role `KTT` (Kế toán trưởng), ghi `approved_by` và `approved_at` |
| Quản lý dữ liệu PO | `backend/app/routers/purchase_orders.py` | CRUD cho `purchase_orders` và `matching_results` |
| AI Cảnh báo bất thường | `ai-service/app/services/anomaly.py` | Dùng `scikit-learn` Isolation Forest, trích xuất đặc trưng (số tiền, tần suất, thuế) |
| AI Đối chiếu PO | `ai-service/app/services/matching.py` | Nhúng văn bản bằng `bge-m3` (HuggingFace), tính Cosine Similarity, ngưỡng ≥ 0.85 |
| Xuất Excel bảng kê | `backend/app/services/export_excel.py` | Dùng `openpyxl`, đổ dữ liệu vào file mẫu cố định (Template), điền tổng cộng |
| Giao diện PO & Báo cáo | `frontend/src/pages/approvals/`, `pages/po/` | Bảng hàng chờ duyệt, form nhập PO, nút tải file Excel, Dashboard (Chart.js) |

**Cơ chế đối chiếu bằng Vector (bge-m3).** Vì tên mặt hàng trên hóa đơn đôi khi viết tắt so với PO (ví dụ: "Laptop ThinkPad T14" vs "Máy tính xách tay Lenovo ThinkPad T14"), việc so khớp chuỗi (regex/RapidFuzz) kém hiệu quả. `bge-m3` sinh embedding vector cho hai chuỗi và tính độ tương đồng cosine. Nếu điểm ≥ 85%, hệ thống tự động map hai dòng này với nhau, đối chiếu số lượng/đơn giá và ghi nhận chênh lệch (nếu có) vào `amount_difference`.

**Mô hình Isolation Forest.** Huấn luyện trước trên một tập 500 hóa đơn giả (tỉ lệ 5% cố ý làm nhiễu số tiền lớn đột biến hoặc lặp lại nhà cung cấp trong ngày). Mô hình chấm điểm bất thường (Anomaly Score từ -1 đến 1, trong đó < 0 là bất thường).

## 3. Kết quả thử nghiệm

### 3.1. Luồng chức năng & Backend

| Thử nghiệm | Kết quả |
|---|---|
| Phân quyền giao diện và API | 100% tài khoản Kế toán viên bị chặn nút "Duyệt" và API `/approve` trả về 403 Forbidden. |
| Xuất bảng kê 01-2/GTGT | Đổ thành công 50 hóa đơn `da_duyet` vào file Excel mẫu. Các cột số liệu (Doanh số, Thuế) định dạng đúng số, hàm SUM() hoạt động chuẩn. Không xuất trùng hóa đơn cũ nhờ cờ `export_status`. |
| Cập nhật trạng thái luồng | Hóa đơn từ `cho_duyet` -> `da_duyet` hoặc `tu_choi` được ghi log đủ `approved_by` (ID người duyệt) và lý do từ chối. |

### 3.2. Đánh giá Mô hình AI (Đo trên tập dữ liệu mẫu nhỏ)

Đo bằng script tự động trên tập 30 hóa đơn ghép với 20 PO (được sinh bằng kịch bản giả lập):

| Cấu hình / Tác vụ | Tiêu chí | Kết quả | Ghi chú |
|---|---|---|---|
| So khớp ngữ nghĩa (bge-m3) | Khớp đúng dòng (Precision) | 26/28 (92.8%) | Xử lý tốt từ đồng nghĩa/viết tắt. |
| So khớp ngữ nghĩa (bge-m3) | Bỏ sót (False Negative) | 2/30 (6.6%) | Có 2 dòng mặt hàng bị miss do mô tả quá ngắn (dưới 3 chữ). Thời gian chạy ~1.2s/hóa đơn trên CPU. |
| Isolation Forest | Cảnh báo đúng bất thường | 5/6 (83%) | Phát hiện tốt số tiền vượt 3 độ lệch chuẩn so với lịch sử chi tiêu của nhà cung cấp. |
| Isolation Forest | Cảnh báo sai (False Positive) | 3/24 (12.5%) | Một số giao dịch lớn hợp lệ vẫn bị đánh dấu vàng. KTT phải tự phán đoán. |

**Nhận xét:**
- `bge-m3` xử lý đối chiếu thông minh hơn hẳn so với việc bắt kế toán map tay, đặc biệt vượt trội với tiếng Việt, tuy nhiên do mô hình khá nặng (~2GB) nên tốn RAM khi khởi động `ai-service`.
- Cảnh báo bất thường làm tốt vai trò "hỗ trợ quyết định". Khả năng False Positive (báo nhầm) là 12.5%, ở mức chấp nhận được vì thao tác quyết định cuối cùng vẫn thuộc về con người (Kế toán trưởng).

## 4. Hạn chế đã biết

- Isolation Forest hiện chưa được huấn luyện lặp lại (retrain) khi có dữ liệu mới. Lâu dài hệ thống sẽ không nhận diện được "hành vi chi tiêu mới" trừ khi được chạy script huấn luyện định kỳ.
- Tính năng đẩy thẳng lên Google Sheets hiện yêu cầu API Key tĩnh của hệ thống, chưa hỗ trợ luồng OAuth cá nhân để xuất vào Drive của riêng từng kế toán.
- `bge-m3` chạy trên CPU khá chậm với hóa đơn có nhiều dòng (trên 20 dòng vật tư). Nếu mở rộng, cần cơ chế cache hoặc chuyển sang batch processing.
- Việc nhập PO vẫn còn khá thủ công, tính năng upload file CSV cho PO chưa xử lý được các file có cấu trúc cột dị biệt.

## 5. Lỗi gặp phải và cách sửa

| # | Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|---|
| 1 | Màn hình trắng trang khi refresh (F5) | Vite/React Router dùng BrowserRouter, web server nội bộ không tìm thấy file route. | Cấu hình catch-all trong Vite (`dev server`) và fallback về `index.html`. |
| 2 | Nút duyệt lúc nào cũng báo 403 Forbidden dù đã login. | Component Layout lấy token giả (mock) thay vì đọc JWT thật từ bước A2 của Hiển. | Viết lại custom hook `useAuth()` để giải mã JWT, lấy role thật (`payload.role`) từ LocalStorage. |
| 3 | Lỗi định dạng số khi xuất file Excel (`openpyxl`). | Giá trị chèn vào ô là kiểu `str` (chuỗi) nên Excel báo lỗi có dấu tam giác xanh (Number stored as text). | Ép kiểu `float()` hoặc `Decimal()` trước khi gán `cell.value` trong Python. |
| 4 | Cột tổng cộng trong file Excel không nhảy số tự động. | Chỉ đổ dữ liệu thô nhưng mất các công thức đã định sẵn trong file Template. | Khôi phục công thức `SUM()` động bằng mã Python dựa trên số dòng đã ghi vào (`sheet[f'E{max_row}'] = f'=SUM(E2:E{max_row-1})'`). |
| 5 | Lỗi tràn bộ nhớ (OOM) khi khởi động `ai-service`. | PaddleOCR (Gói A) và `bge-m3` cùng load lên RAM máy tính cục bộ (8GB). | Khởi tạo mô hình ở chế độ lazy-loading (chỉ tải `bge-m3` khi có request `match-po` đầu tiên) và giải phóng (del) sau 30 phút rảnh. |
| 6 | Lỗi chênh lệch 1-2 đồng khi đối chiếu tiền PO. | Sai số do làm tròn số thập phân (float) trong CSDL và lúc tính tổng bằng code. | Thống nhất dùng thư viện `decimal.Decimal` cho toàn bộ logic đối chiếu tiền tệ và ép kiểu trong CSDL sang `DECIMAL(18,2)`. |