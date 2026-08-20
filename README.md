# AI Invoice Accounting

AI-assisted invoice/document entry system for accounting — graduation project.

## Goal

Automate reading, extracting, matching, and posting journal entries for
invoices, reducing manual data entry time and errors for accountants.

## 7 Core Functions

1. Invoice capture & digitization (OCR)
2. Structured data extraction (vendor, date, amount, tax ID...)
3. Context normalization (NLP) — understand different phrasing across vendors
4. Confidence scoring for extracted data
5. Document matching (2-way/3-way matching)
6. GL Coding — suggest Debit/Credit entries following Circular 133/2016/TT-BTC
7. Reporting & spending trend analysis

## Folder Structure

```
ai-invoice-accounting/
├── ai-service/     # Python service for OCR + LLM data extraction
├── backend/        # Main API: business logic, database, approval workflow
├── frontend/       # Web UI: upload, confirmation, dashboard
├── database/       # Schema, migrations, seed data (Chart of Accounts per TT133)
└── docs/           # Project report, organized by chapter
```

## Tech Stack

| Component  | Technology                                                     |
| ---------- | -------------------------------------------------------------- |
| AI Service | Python + FastAPI, Google Cloud Vision API / Tesseract, LLM API |
| Backend    | Python + FastAPI, SQLAlchemy, Alembic                          |
| Frontend   | React + Vite + Tailwind CSS                                    |
| Database   | MySQL 8.0 (via Docker)                                         |

See [`SETUP.md`](./SETUP.md) for detailed setup instructions — especially
the MySQL configuration section, to avoid charset/connection issues when
the team works together.

## Setup Guide

### Step 0: Install Docker (if not already installed)

The project uses Docker to run MySQL — this ensures all 3 team members run
the exact same MySQL version, avoiding config mismatches between machines.

- **Windows/Mac:** download Docker Desktop at
  https://www.docker.com/products/docker-desktop → install like any normal
  app → open it and wait until the whale icon stops loading (Docker is ready)
- **Linux:** install Docker Engine following
  https://docs.docker.com/engine/install/

Verify installation:

```bash
docker --version
docker compose version
```

### Step 1: Create the single `.env` file and start MySQL

There is exactly **one** `.env` file for the whole project, at the root.
Docker Compose, the backend, and the AI service all read from it.

```bash
cp .env.example .env    # fill in real values, or keep the defaults for local dev
docker compose up -d mysql
```

The first run takes a few minutes to pull the MySQL 8.0 image.

Check MySQL is ready:

```bash
docker compose ps        # status should be "healthy"
docker compose logs mysql
```

### Step 2: Run the AI Service

```bash
cd ai-service
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

(No separate `.env` needed here — it reads the root `.env` automatically.)

### Step 3: Run the Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

(Also reads the root `.env` automatically — no local `.env` file needed.)

### Step 4: Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

### Daily startup order

```bash
docker compose up -d mysql
# then open 3 separate terminals for backend, ai-service, frontend
```

See [`SETUP.md`](./SETUP.md) for the full list of MySQL stability
practices (charset, money data type, connection pooling, migrations).
