# Database

Contains schema, migrations, and seed data.

## Important seed data: Chart of Accounts

Seed the account list per Appendix 1, Circular 133/2016/TT-BTC (or
200/2014/TT-BTC if the team targets larger enterprises instead).

Reference source:
- https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Thong-tu-133-2016-TT-BTC-huong-dan-che-do-ke-toan-doanh-nghiep-nho-va-vua-284997.aspx

## Planned files
```
database/
├── schema.sql                    # DDL for the main tables
├── seed_chart_of_accounts.sql    # Sample account list (111, 112, 331, 642, 156...)
└── er-diagram.png                # ERD (exported from Chapter 3 of the report)
```
