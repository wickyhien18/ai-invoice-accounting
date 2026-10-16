# database/

- `seed/chart_of_accounts_tt133.csv`: danh sách tài khoản kế toán dùng cho bảng `chart_of_accounts`
  (mã tài khoản, tên). Đây là bản tham khảo gồm các tài khoản hay dùng khi nhập hóa đơn. **Cần đối chiếu
  với văn bản Thông tư 133/2016/TT-BTC** (tên và mã tài khoản) trước khi dùng cho báo cáo.
- Nạp vào CSDL (chạy trong `backend/`, sau khi đã `alembic upgrade head`):
  ```bash
  python scripts/seed_coa.py
  ```
- Cấu trúc bảng nằm trong `backend/app/models/` và migration trong `backend/alembic/versions/`.
