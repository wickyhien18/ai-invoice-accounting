# AI Invoice Accounting

AI-assisted invoice/document entry system for accounting (graduation project, Group 15).

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
├── ai-service/     # Python service for OCR + LLM data extraction + ML models
├── backend/        # Main API: business logic, database, approval workflow
├── frontend/       # Web UI: upload, review, approval, dashboard
├── database/       # Schema, migrations, seed data (Chart of Accounts per TT133)
├── data_test/      # 12 synthetic sample invoices + labels (pdf/images/xml)
├── tools/          # Synthetic test-invoice generator and scoring script
└── docs/           # Work assignment (PHAN_CONG.md) and project report
```

## Tech Stack

| Area | Component | Technology |
| ---- | --------- | ---------- |
| Platform | AI Service | Python 3.12 + FastAPI, Pillow |
| Platform | Backend | Python 3.12 + FastAPI, SQLAlchemy, Alembic, PyMySQL, JWT, bcrypt |
| Platform | Frontend | React + Vite + Tailwind CSS (Node.js 20 LTS) |
| Platform | Database | MySQL 8.0 (via Docker), `DECIMAL(18,2)` for money |
| Platform | Environment | Docker Compose, a single `.env` file at the project root |
| Platform | Source control | Git + GitHub (protected `main`, Pull Request required) |
| Platform | Input / output | XML e-invoices read directly; export to Google Sheet / Excel (form 01-2/GTGT) |
| Platform | Diagrams | PlantUML, dbdiagram.io |
| AI | OCR | PaddleOCR (runs locally, Vietnamese model) |
| AI | LLM | Gemini Flash via free tier (Google AI Studio API key) |
| AI | Name / address normalization | RapidFuzz |
| AI | Document type classification | Logistic Regression (scikit-learn) |
| AI | GL coding (Debit/Credit suggestion) | TF-IDF + Logistic Regression (scikit-learn) |
| AI | Purchase-order matching | bge-m3 (sentence-transformers) |
| AI | Anomaly / duplicate detection | Isolation Forest (scikit-learn) |

See [`SETUP.md`](./SETUP.md) for detailed setup instructions — especially
the MySQL configuration, the `.env` variables, and the AI Service
(model downloads, Gemini API key) sections.

> **Privacy:** the Gemini free tier may use submitted data to improve
> Google's products. Only send synthetic or masked sample invoices (tax ID
> and company names hidden). Never send real customer invoices, and never
> commit real invoice images to GitHub.

## Setup Guide

### Step 0: Install Python, Node.js, Docker (if not already installed)

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

**Install Python 3.12 specifically.** Newer versions (for example 3.14) do
not have pre-built packages for some libraries yet, and `pip install` then
fails while trying to compile them.

_Windows_

- Go to https://www.python.org/downloads/release/python-3120/
- Scroll down and download "Windows installer (64-bit)"
- Run the installer and **check the box "Add python.exe to PATH" before
  clicking Install** (easy to miss, but important)
- Verify:

```bash
python --version
```

_Mac_

```bash
brew install python@3.12
```

(If you don't have Homebrew, install it first from https://brew.sh)

Verify:

```bash
python3.12 --version
```

_Linux (Ubuntu/Debian)_

```bash
sudo apt update
sudo apt install python3.12 python3.12-venv
```

_Linux (Arch/CachyOS)_

```bash
sudo pacman -S python312
```

If not available in the official repos:

```bash
yay -S python312
```

**Node.js (version 20 LTS)**

_Windows / Mac_

- Go to https://nodejs.org
- Download the button labeled "LTS" (20.x or 22.x — either LTS version works for this project)
- Run the installer, keep the default options, and click through to finish
- Verify:

```bash
node --version
npm --version
```

_Mac (via Homebrew, alternative)_

```bash
brew install node@20
```

_Linux (Ubuntu/Debian) — using NodeSource (recommended over apt's outdated version)_

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

_Linux (Arch/CachyOS)_

```bash
sudo pacman -S nodejs npm
```

**Quick summary — one command to check everything at once**

```bash
echo "Python: $(python3.12 --version 2>/dev/null || echo 'NOT INSTALLED')"
echo "Node:   $(node --version 2>/dev/null || echo 'NOT INSTALLED')"
echo "Docker: $(docker --version 2>/dev/null || echo 'NOT INSTALLED')"
```

On Windows (PowerShell) run the three `--version` commands one by one instead.

**Optional: MySQL Workbench (if you don't want to use MySQL in the terminal)**

_Windows_

1. Download: go to https://dev.mysql.com/downloads/workbench/, make sure
   "Microsoft Windows" is selected, and click Download next to the `.msi`
   installer. If it asks you to log in, click the small link
   "No thanks, just start my download" at the bottom.
2. Install: run the `.msi`, keep default settings. If it asks about the
   Visual C++ Redistributable, click Yes — Workbench needs it.
3. Launch "MySQL Workbench" from the Start Menu.

_Mac_

1. Download from the same page, choose macOS, then the right build for your
   chip: ARM 64-bit DMG for Apple Silicon (M1–M4), x86 64-bit DMG for Intel.
   Click "No thanks, just start my download" to skip login.
2. Open the `.dmg` and drag MySQL Workbench into Applications.
3. First launch only: macOS may block it. Go to System Settings →
   Privacy & Security, click "Open Anyway" next to the MySQL Workbench
   message, then confirm with Open.

_Linux — Ubuntu / Debian_

```bash
sudo apt update
sudo apt install mysql-workbench
```

(or search "MySQL Workbench" in Ubuntu Software and click Install)

_Linux — Arch / CachyOS_

```bash
sudo pacman -S mysql-workbench
# if not found, use an AUR helper:
yay -S mysql-workbench
```

**Connect Workbench to the Docker MySQL**

MySQL runs inside Docker (after `docker compose up -d mysql`) but is still
reachable at `localhost:3306`.

1. Open MySQL Workbench and click the "+" next to "MySQL Connections"
2. Fill in: Connection Name `AI Invoice Accounting`, Hostname `127.0.0.1`,
   Port `3306`, Username = your `MYSQL_USER` value from `.env`
3. Click "Test Connection", enter your `MYSQL_PASSWORD` value, and tick
   "Save password"
4. Click OK, then double-click the new connection

You will see all databases including `ai_invoice_db`, with a table browser,
SQL editor, and ER diagram tool.

### Step 1: Create the single `.env` file and start MySQL

There is exactly **one** `.env` file for the whole project, at the root.
Docker Compose, the backend, and the AI service all read from it.

```bash
cp .env.example .env    # then fill in real values (see SETUP.md section 4)
docker compose up -d mysql
```

On Windows PowerShell use `copy .env.example .env`.

The first run takes a few minutes to pull the MySQL 8.0 image.

Check MySQL is ready:

```bash
docker compose ps        # status should be "healthy"
docker compose logs mysql
```

### Step 2: Get a Gemini API key (free tier)

1. Open https://aistudio.google.com/apikey and sign in with a Google account
2. Create an API key and copy it
3. Put it in your own `.env` as `GEMINI_API_KEY=...` (never commit it)

Each team member can create their own key. Free-tier limits change often;
check https://ai.google.dev/gemini-api/docs/rate-limits for the current
limits of the model you use.

### Step 3: Run the AI Service

```bash
cd ai-service
python3.12 -m venv venv           # Windows: py -3.12 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

The first run downloads the OCR models, so it needs internet and takes
longer. For the machine-learning packages (scikit-learn, sentence-transformers)
and the full AI Service notes, see [`SETUP.md`](./SETUP.md) section 3.1.

### Step 4: Run the Backend

```bash
cd backend
python3.12 -m venv venv           # Windows: py -3.12 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head              # create all 9 tables
python scripts/seed_demo.py       # dev only: CoA + demo users (see SETUP.md 3.2)
uvicorn app.main:app --reload --port 8000
```

### Step 5: Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at http://localhost:5173 by default (Vite).

### Daily startup order

```bash
docker compose up -d mysql
# then open 3 separate terminals: backend (8000), ai-service (8001), frontend (5173)
```

## Test data

Real invoices from hoadondientu are not available for development, so the
project uses synthetic invoices with ground-truth labels. See
[`SETUP.md`](./SETUP.md) section 6 to generate them and score OCR/LLM
output.

## Working with Git

`main` is protected: deleting the branch and force pushes are blocked, and
changes must come through a Pull Request.

```bash
git checkout -b feature/short-description
git add <files>
git commit -m "Describe the change"
git push -u origin feature/short-description
# then open a Pull Request on GitHub and ask a teammate to review
```

Never commit `.env`, API keys, or real invoice images.

See [`SETUP.md`](./SETUP.md) for the full list of MySQL stability
practices (charset, money data type, connection pooling, migrations) and
troubleshooting.
