# Setup Guide — ai-invoice-accounting

Confirmed stack:
- **Backend:** Python + FastAPI
- **AI Service:** Python + FastAPI
- **Frontend:** React + Tailwind CSS
- **Database:** MySQL

This document walks each team member through local setup, and explains
how MySQL is configured to avoid common pitfalls (dropped connections,
wrong charset, rounding errors on money values).

---

## 0. Prerequisites

Install on your machine:
- Python 3.11+
- Node.js 20 LTS+
- Docker Desktop (recommended for running MySQL — avoids inconsistent
  local MySQL installs across the 3 team members)
- Git

Verify:
```bash
python3 --version
node --version
docker --version
```

---

## 1. MySQL — running it reliably with Docker (recommended)

**Why Docker instead of installing MySQL directly:** all 3 team members
run the exact same MySQL version, avoiding the classic "works on my
machine" problem — usually caused by different MySQL versions or a
different default charset.

### 1.1. `docker-compose.yml` (at the project root)

See the `docker-compose.yml` file already included in the repo. Key
points to understand:

- `MYSQL_CHARACTER_SET=utf8mb4` — **required** to correctly store
  non-ASCII text (e.g. names with special characters or accented
  letters). The old MySQL default (`latin1`) corrupts such text into
  `?` or garbled characters.
- `volumes` — MySQL data is stored outside the container, so data
  survives container restarts/removal (it's not wiped every time you
  run `docker compose down`).
- `healthcheck` — Docker automatically checks whether MySQL is ready to
  accept connections, preventing the backend from starting and
  connecting before MySQL has finished booting (a very common
  "Connection refused" error right after `docker compose up`).

### 1.2. Start MySQL

```bash
docker compose up -d mysql
```

Check it's running:
```bash
docker compose ps
docker compose logs mysql
```

### 1.3. Test the connection

```bash
docker exec -it ai-invoice-mysql mysql -u app_user -p ai_invoice_db
# enter the password from your .env file
```

---

## 2. Principles for keeping MySQL stable throughout the project

This is the most important section — apply these from day one to avoid
having to rebuild the whole database midway through the project because
of an initial configuration mistake.

### 2.1. Always use `utf8mb4`, never `utf8`

In MySQL, the charset literally named `utf8` is a legacy shorthand that
**cannot store some characters correctly**. Always declare:
```sql
CREATE DATABASE ai_invoice_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

### 2.2. Money columns — never use FLOAT/DOUBLE

A very common mistake for students building a finance system: using
`FLOAT` to store money causes **rounding errors** (e.g. two amounts
that should sum to 2000 end up as 1999.9999999). For an accounting
system, money **must** use `DECIMAL`:
```sql
amount DECIMAL(18, 2) NOT NULL
```
`DECIMAL(18,2)` means up to 18 total digits, 2 after the decimal point
— enough for large amounts without rounding errors.

### 2.3. Connection pooling in the FastAPI backend

If the backend opens a new connection per request without closing it
properly, MySQL will eventually throw "Too many connections" once
multiple people test simultaneously (including during the thesis
defense demo if all 3 members test at once). Use SQLAlchemy with a
pre-configured connection pool (see `backend/app/database.py`) instead
of manually managing raw `mysql-connector` connections in each route.

### 2.4. Always use migrations (Alembic), never edit the schema by hand

When all 3 people modify table structures without migrations, each
person's local database gradually drifts apart, causing hard-to-debug
errors. Use **Alembic** so every schema change is recorded as a file
and synced through Git.

### 2.5. Back up before testing with large datasets

Before importing many sample invoices for testing, back up first:
```bash
docker exec ai-invoice-mysql mysqldump -u app_user -p ai_invoice_db > backup.sql
```

---

## 3. Setting up each component

### 3.1. AI Service (`ai-service/`)

```bash
cd ai-service
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```
No local `.env` file is needed — it automatically loads the single root
`.env` (see section 4).

### 3.2. Backend (`backend/`)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head            # create tables from the latest migration
uvicorn app.main:app --reload --port 8000
```
Also reads the root `.env` automatically — no local `.env` file needed.

### 3.3. Frontend (`frontend/`)

```bash
cd frontend
npm install
npm run dev
```

---

## 4. Environment variables (`.env`) — single file for the whole project

### 4.1. What `.env` is and why there is only one

The project uses **exactly one** `.env` file, located at the project
root. It holds every variable needed by MySQL (via docker-compose), the
backend, and the AI service — instead of maintaining three separate
`.env` files that can drift out of sync (which was the original,
error-prone setup).

`backend/app/database.py` and `ai-service/app/main.py` both explicitly
load this root `.env` file by resolving its path relative to their own
location — you do not need to copy `.env` into each subfolder.

`.env.example` is the **template** (no real secrets, safe to commit to
Git). Each team member copies it once to `.env` (already excluded via
`.gitignore`, so Git will never push it).

### 4.2. Create your `.env` file

```bash
cp .env.example .env
```
That's it — one command, run once at the project root.

### 4.3. What each variable means

| Variable | Used by | Meaning |
|---|---|---|
| `MYSQL_ROOT_PASSWORD` | docker-compose | Password for MySQL's `root` (full-access) account |
| `MYSQL_DATABASE` | docker-compose | Database name created automatically on first MySQL startup |
| `MYSQL_USER` / `MYSQL_PASSWORD` | docker-compose | App-specific MySQL account (never connect using `root` from code) |
| `DB_HOST` | backend | MySQL host — `localhost` since Docker maps the port to your machine |
| `DB_PORT` | backend | MySQL port, default `3306` |
| `DB_USER` / `DB_PASSWORD` / `DB_NAME` | backend | **Must exactly match** the `MYSQL_*` values above — a mismatch causes "Access denied" errors |
| `SECRET_KEY` | backend | Secret string used to sign JWT tokens (login). Use a long random string, especially before any real deployment |
| `AI_SERVICE_URL` | backend | Address the backend uses to call the AI service, default `http://localhost:8001` |
| `GOOGLE_APPLICATION_CREDENTIALS` | ai-service | Path to the Google Cloud Vision API JSON key (leave blank if using Tesseract instead) |
| `LLM_API_KEY` | ai-service | API key for OpenAI/Claude, used to parse invoice data. **Never commit a real key to Git** |
| `LLM_MODEL` | ai-service | Which LLM model to call, e.g. `gpt-4o-mini` |

### 4.4. Common `.env`-related errors

- **Backend reports "Access denied for user"** → `DB_USER`/`DB_PASSWORD`
  don't match `MYSQL_USER`/`MYSQL_PASSWORD` — double-check they're identical
- **`docker compose up` doesn't seem to read `.env`** → you must run the
  command from the project root (where both `.env` and
  `docker-compose.yml` live), not from a subfolder
- **Changed `.env` but MySQL still uses the old password** → MySQL only
  reads `MYSQL_ROOT_PASSWORD`/`MYSQL_PASSWORD` the **first time** the
  container is created. If you change them afterward, run
  `docker compose down -v` (this wipes the volume) then
  `docker compose up -d mysql` again so MySQL re-initializes with the
  new values
- **Accidentally committed a real `.env` to GitHub** → rotate that
  password/API key immediately (treat it as compromised), then remove it
  from Git history with `git rm --cached .env` and commit again

---

## 5. Daily startup order

```bash
docker compose up -d mysql       # 1. start the database first
cd backend && uvicorn app.main:app --reload --port 8000 &   # 2. start backend
cd ai-service && uvicorn app.main:app --reload --port 8001 & # 3. start AI service
cd frontend && npm run dev       # 4. start frontend last
```
