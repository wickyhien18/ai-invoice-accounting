# Database

Chứa schema, migration và seed data.

## Seed data quan trọng: Chart of Accounts (Danh mục tài khoản)

Cần seed sẵn danh mục tài khoản theo Phụ lục 1, Thông tư 133/2016/TT-BTC
(hoặc TT200/2014/TT-BTC nếu nhóm chọn áp dụng cho doanh nghiệp lớn hơn).

Nguồn tài khoản chuẩn:
- https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Thong-tu-133-2016-TT-BTC-huong-dan-che-do-ke-toan-doanh-nghiep-nho-va-vua-284997.aspx

## File dự kiến
```
database/
├── schema.sql              # DDL các bảng chính
├── seed_chart_of_accounts.sql   # Danh mục tài khoản mẫu (111, 112, 331, 642, 156...)
└── er-diagram.png          # Sơ đồ ERD (xuất từ Chương 3 đồ án)
```
