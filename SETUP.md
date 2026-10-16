# Setup Guide — ai-invoice-accounting

Confirmed stack:
- **Backend:** Python 3.12 + FastAPI, SQLAlchemy, Alembic
- **AI Service:** Python 3.12 + FastAPI — PaddleOCR (OCR, local), Gemini Flash (LLM, free tier),
  scikit-learn / sentence-transformers / RapidFuzz (ML and matching)
- **Frontend:** React + Vite + Tailwind CSS
- **Database:** MySQL 8.0 (Docker)

This document walks each team member through local setup, and explains
how MySQL is configured to avoid common pitfalls (dropped connections,
wrong charset, rounding errors on money values). The README has the
step-by-step installation of Python, Node.js, Docker and MySQL Workbench;
this file covers configuration and the AI Service in detail.

---

## 0. Prerequisites

Install on your machine:
- Python **3.12** (not newer: some libraries have no pre-built packages for
  3.13/3.14 yet, so `pip install` tries to compile them and fails)
- Node.js 20 LTS+
- Docker Desktop (recommended for running MySQL — avoids inconsistent
  local MySQL installs across the 3 team members)
- Git
- Free disk space: a few GB (PyTorch and the embedding model used for
  purchase-order matching are large)

Verify:
```bash
python3.12 --version     # Windows: py -3.12 --version
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

- `command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci`
  — **required** to correctly store Vietnamese text and other non-ASCII
  characters. The old MySQL default (`latin1`) corrupts such text into
  `?` or garbled characters. (This is a server startup flag; there is no
  `MYSQL_CHARACTER_SET` environment variable.)
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
of manually managing raw connections in each route.

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

The AI Service does the heavy work: OCR with PaddleOCR (local), data
extraction with the Gemini API, and the machine-learning models (GL coding,
purchase-order matching, anomaly detection). XML e-invoices are read
directly by the backend/AI Service without OCR.

```bash
cd ai-service
python3.12 -m venv venv           # Windows: py -3.12 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
python -m pip install --upgrade pip
```

**Windows PowerShell:** if activating the venv is blocked by script
policy, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

**Check you are in the right venv (do this every time, before installing or testing).**
`backend/` and `ai-service/` each have their own folder named `venv`, so the
`(venv)` shown in your prompt does NOT tell you which one is active. Packages
installed into the backend venv are invisible to the AI Service and vice versa.
```bash
which python          # Windows PowerShell: (Get-Command python).Source
python --version
```
- The path must end with `ai-service/venv/bin/python` (Windows:
  `ai-service\venv\Scripts\python.exe`). If it points to `backend/venv` or
  `/usr/bin/python`, run `deactivate`, then `cd` into `ai-service` and activate
  again.
- The version must be `Python 3.12.x`.
- Keep the same terminal (still activated) for all the checks below. After
  `deactivate`, `python` is the system Python and every `import` will fail
  with `No module named ...`.
- Always install with `python -m pip ...` (not bare `pip`), so packages go into
  the Python you just checked.

**a) PaddlePaddle (the engine PaddleOCR runs on) — install first, CPU build:**
```bash
python -m pip install paddlepaddle==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
python -c "import paddle; print(paddle.__version__)"
```
It should print a version number. If pip cannot find a build for your
Python version or OS, tell the team before changing anything (see section 7).
Installation was checked against the PaddlePaddle docs, not on every
operating system, so each member should run this check.

**b) Core packages:**
```bash
python -m pip install -r requirements.txt
```
`requirements.txt` holds: FastAPI, Uvicorn, python-dotenv, Pillow,
`paddleocr`, `google-genai` (Gemini SDK), and RapidFuzz.

Verify that PaddleOCR was really installed (an outdated `requirements.txt`
without the `paddleocr` line installs everything else without any error):
```bash
python -m pip show paddleocr      # must print a "Version:" line
python -c "import fastapi, PIL, rapidfuzz, google.genai, paddle, paddleocr; print('ai-service deps OK')"
```
If it prints `WARNING: Package(s) not found`, run `git pull` to get the latest
`requirements.txt`, or install it directly: `python -m pip install paddleocr`.

**c) Machine-learning packages (needed for GL coding, PO matching and anomaly detection):**
```bash
# Windows/Linux: install the CPU build of PyTorch first to avoid a huge download
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-ml.txt
```
`requirements-ml.txt` holds: scikit-learn and sentence-transformers.
macOS users can skip the `torch` line (the normal `python -m pip install` works).

**d) First-run downloads.** The first time the service runs it downloads:
- the PaddleOCR Vietnamese text-recognition model (needs internet);
- the `bge-m3` embedding model when purchase-order matching is first
  used (large, around a few GB of disk — download it once on a good connection).

Check that PaddleOCR loads (this triggers the model download):
```bash
python -c "from paddleocr import PaddleOCR; PaddleOCR(lang='vi'); print('PaddleOCR OK')"
```
A `UserWarning: No ccache found` message is harmless; ignore it.

**e) Gemini API key.** Create a key at https://aistudio.google.com/apikey
and put it in the root `.env` as `GEMINI_API_KEY` (section 4).

**f) Run the service:**
```bash
uvicorn app.main:app --reload --port 8001
```
No local `.env` file is needed — it automatically loads the single root
`.env` (see section 4).

> **Privacy:** the Gemini free tier may use submitted data to improve
> Google's products. Only send synthetic or masked invoices (tax ID and
> company names hidden). Free-tier limits change often; check
> https://ai.google.dev/gemini-api/docs/rate-limits.

### 3.2. Backend (`backend/`)

Run these inside `backend/` with the **backend** venv active (`which python`
must end with `backend/venv/bin/python`). The `python -c` line right after
the install prints `backend deps OK` only if every package is importable; if
it fails, the message names the missing one.

```bash
cd backend
python3.12 -m venv venv           # Windows: py -3.12 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
python -m pip install -r requirements.txt
python -c "import fastapi, sqlalchemy, alembic, pymysql, jwt, bcrypt; print('backend deps OK')"
alembic upgrade head            # create tables from the latest migration
uvicorn app.main:app --reload --port 8000
```
Also reads the root `.env` automatically — no local `.env` file needed.
`alembic upgrade head` creates all 9 tables of the ERD (migration `0001`).

Seed data (run inside `backend/`, MySQL must be up):

```bash
python scripts/seed_coa.py     # load the Chart of Accounts (TT133) - safe to re-run
python scripts/seed_demo.py    # DEV ONLY: seed_coa + 2 demo users
                               # ktv@demo.local / ktv12345 (KTV), ktt@demo.local / ktt12345 (KTT)
```

Check it works: open http://localhost:8000/api/health and
http://localhost:8000/docs. Most business endpoints are **mock** for now
(`"mock": true` in the response) — see `docs/PHAN_CONG.md`. Run tests with
`pytest` (they use a temporary SQLite file, no MySQL needed).

### 3.3. Frontend (`frontend/`)

```bash
cd frontend
npm install
npm run dev
```
Opens at http://localhost:5173 by default.

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
cp .env.example .env              # Windows PowerShell: copy .env.example .env
```
That's it — one command, run once at the project root. Then fill in your
own `GEMINI_API_KEY`.

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
| `ACCESS_TOKEN_EXPIRE_MINUTES` | backend | JWT lifetime in minutes, default `480` |
| `UPLOAD_DIR` | backend | Where uploaded invoice files are stored, default `storage/uploads` (git-ignored) |
| `AI_SERVICE_URL` | backend | Address the backend uses to call the AI service, default `http://localhost:8001` |
| `GEMINI_API_KEY` | ai-service | Your own Gemini API key from Google AI Studio. **Never commit a real key to Git** |
| `LLM_MODEL` | ai-service | Which Gemini Flash model to call. Use the current Flash model name shown in the Gemini API docs (https://ai.google.dev/gemini-api/docs/quickstart) and make sure it has a free tier |

Optional, only when the Google Sheet export feature is implemented: a path
to a Google service-account JSON key. Add the variable name used in the code
to `.env.example` at that time.

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
- **Using an old `.env.example` copy** → download or pull the latest from
  Git; an old 4-line version will miss variables such as `GEMINI_API_KEY`
- **Accidentally committed a real `.env` to GitHub** → rotate that
  password/API key immediately (treat it as compromised), then remove it
  from Git history with `git rm --cached .env` and commit again

---

## 5. Daily startup order

Open a separate terminal for each service (works the same on Windows,
Mac and Linux):

```bash
# 1. database (from the project root)
docker compose up -d mysql

# 2. backend — terminal 2
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# 3. AI service — terminal 3
cd ai-service && source venv/bin/activate && uvicorn app.main:app --reload --port 8001

# 4. frontend — terminal 4
cd frontend && npm run dev
```
(Windows: activate with `venv\Scripts\activate` instead of `source venv/bin/activate`.)

Ports: backend 8000, AI service 8001, frontend 5173, MySQL 3306.

---

## 6. Test data (synthetic invoices)

Real invoices from hoadondientu are not available during development, so
the team tests OCR and the LLM on **synthetic invoices with known answers**.
The generator and scorer live in `tools/`.

**Requirements:** `python -m pip install reportlab pillow numpy` (inside any venv) and
`pdftoppm` from Poppler:
- Windows: download Poppler for Windows and add its `bin` folder to PATH
- Mac: `brew install poppler`
- Ubuntu/Debian: `sudo apt install poppler-utils`
- Arch/CachyOS: `sudo pacman -S poppler`

The generator draws with DejaVu fonts and loads `FONT_DIR + "DejaVuSans.ttf"`,
so `FONT_DIR` (at the top of `tools/gen_invoices.py`) must be the folder that
contains `DejaVuSans.ttf`, **ending with a `/`**. The default path only exists
on Ubuntu/Debian. On any other system, install the font and set `FONT_DIR`:
- Ubuntu/Debian: `sudo apt install fonts-dejavu-core`
  (folder `/usr/share/fonts/truetype/dejavu/`)
- Arch/CachyOS: `sudo pacman -S ttf-dejavu`
  (folder usually `/usr/share/fonts/TTF/`)
- Windows / macOS: download DejaVu Sans, then point `FONT_DIR` to the folder
  that holds `DejaVuSans.ttf`

To find the real folder on Linux:
```bash
fc-list | grep -i "DejaVuSans.ttf"
```
The path before `DejaVuSans.ttf` is your `FONT_DIR`.

**Generate 40 invoices** (PDF, images — about 60% degraded to look like phone
photos —, simplified XML, and labels):
```bash
python tools/gen_invoices.py --n 40 --out data_test --seed 1
```
To generate only the bilingual e-invoice layout (closest to the layout of
e-invoices shown on the tax portal: Vietnamese/English labels, column-number
row, digital-signature box, tax-authority code, lookup code), add
`--style portal`. Labels use `mau_so` = `1` and `ky_hieu` = `C26TAA`
(form number kept separate; some invoices print `1C26TAA`, and the scorer
accepts both).

`data_test/` is for local testing — do not commit it if it grows large.
All company names, tax IDs and addresses are fake, and every invoice carries a
"synthetic data" line.

**Score OCR/LLM output.** Save the extracted fields of each invoice as
`pred/HD001.json`, `pred/HD002.json`, ... (fields such as `so_hoa_don`,
`ky_hieu`, `ngay_lap`, `mst_nguoi_ban`, `tong_thanh_toan`), then:
```bash
python tools/score_fields.py --labels data_test/labels.json --pred pred/
```
The output is the accuracy per field, split into clean and degraded images.

**Limits:** the synthetic set has only 3 layouts and is cleaner than real
invoices, so accuracy measured on it is higher than on real invoices.
If the report uses these numbers, state that they come from synthetic data
and a small sample. The XML is a simplified imitation, not validated against
the official schema.

---

## 7. Troubleshooting

- **`pip install` fails while building `pydantic-core` or `pillow`
  (a Rust/wheel build error)** → your Python is too new (for example 3.14).
  Delete the `venv` folder, recreate it with Python 3.12
  (`python3.12 -m venv venv`), and install again.
- **`import paddle` fails or pip finds no `paddlepaddle` build** → check the
  Python version in the active venv (`python --version` must say 3.12), and
  that you used the PaddlePaddle CPU index URL from section 3.1 a). If it still
  fails, tell the team which OS and Python version you have before trying other
  versions, so everyone ends up on the same setup.
- **Some packages are missing after `pip install -r requirements.txt` (for
  example `sqlalchemy`)** → you most likely used bare `pip`, which can belong to
  another venv or the system Python, or you ran the command in the wrong
  folder (each of `backend/` and `ai-service/` has its own
  `requirements.txt`). Run `pwd` and `which python`, then reinstall with
  `python -m pip install -r requirements.txt` and run the `python -c "import ..."`
  check of that component (section 3.1 or 3.2).
- **`ModuleNotFoundError: No module named 'paddle'` or `'paddleocr'`** → work
  through these in order:
  1. Wrong venv or no venv: run `which python`. It must end with
     `ai-service/venv/bin/python` (section 3.1, "Check you are in the right
     venv"). A path under `backend/venv` or `/usr/bin/python` is the cause.
  2. Only `paddleocr` is missing while `import paddle` works: the package was
     never installed, usually because `requirements.txt` is outdated. Run
     `python -m pip show paddleocr`, then `git pull` or
     `python -m pip install paddleocr`.
  3. Only `paddle` is missing: repeat section 3.1 a) inside the right venv.
  4. If you installed into the wrong venv by mistake, remove it there with
     `python -m pip uninstall -y paddlepaddle` (while that venv is active).
- **`TTFError: Can't open file ".../DejaVuSans.ttf"` when running
  `tools/gen_invoices.py`** → the font is not at the default Ubuntu path.
  Install DejaVu and fix `FONT_DIR` as described in section 6.
- **PaddleOCR is slow the first time** → it is downloading models; later
  runs are faster.
- **Gemini returns a quota / 429 error** → you hit the free-tier limit; wait,
  reduce the number of requests, or check the current limits.
- **Gemini returns a "model not found" error** → update `LLM_MODEL` to the
  current Flash model name in the Gemini API docs.
- **`sentence-transformers` or `torch` download is huge or slow** → install the
  CPU build of PyTorch first (section 3.1 c) and do it on a stable connection.
- **Vietnamese text shows as `?` in MySQL** → the database was not created
  with `utf8mb4` (section 2.1).
- **The backend says "Connection refused" for MySQL right after startup** →
  MySQL is still booting; wait until `docker compose ps` shows `healthy`.
