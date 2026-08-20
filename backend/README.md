# Backend

Responsible for:
- Main API for the frontend
- Database (invoices, documents, chart of accounts, journal entries, users)
- Business logic: document matching, GL coding, approval workflow
- Authentication & authorization (JWT)
- Calling `ai-service` to get OCR + extraction results

## Tech Stack
Python + FastAPI, SQLAlchemy (ORM), Alembic (migrations), MySQL, JWT (auth)

## Environment variables
No local `.env` file — reads the single root `.env` (see `../SETUP.md`).

## Main tables to design
- `users` — accountant / chief accountant
- `invoices` — source invoice, processing status
- `invoice_fields` — extracted data with confidence_score
- `chart_of_accounts` — account list per Appendix 1, Circular 133/2016/TT-BTC
- `journal_entries` — journal entries (Debit/Credit)
- `matching_results` — PO – GRN – Invoice matching results
