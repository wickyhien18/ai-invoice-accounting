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

### Step 0: Install Python, NodeJS, Docker (if not already installed)

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

Install Python 3.12 specifically.

Windows

- Go to https://www.python.org/downloads/release/python-3120/
- Scroll down, download "Windows installer (64-bit)"
  -Run the installer — check the box "Add python.exe to PATH" before clicking Install (easy to miss, but important)
- Verify:

```bash
python --version
```

Macs

```bash
brew install python@3.12
```

(If you don't have Homebrew: install it first from https://brew.sh)

Verify:

```bash
python3.12 --version
```

Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3.12 python3.12-venv
```

Linux (Arch/CachyOS — matches your earlier error)

```bash
sudo pacman -S python312
```

If not available in official repos:

```bash
yay -S python312
```

Check if Python is already installed (any OS)

```bash
python3 --version
python3.12 --version
```

Node.js (version 20 LTS)

Windows / Mac

- Go to https://nodejs.org
- Download the button labeled "LTS" (currently 20.x or 22.x — either LTS version works fine for this project)
- Run the installer, keep default options, click through to finish
- Verify:

```bash
node --version
npm --version
```

Mac (via Homebrew, alternative)

```bash
brew install node@20
```

Linux (Ubuntu/Debian) — using NodeSource (recommended over apt's outdated version)

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

Linux (Arch/CachyOS)

```bash
sudo pacman -S nodejs npm
```

Check if Node.js is already installed (any OS)

```bash
node --version
npm --version
```

If you see version numbers (e.g. v20.x.x), it's installed. If command not found, it isn't.

**Quick summary — one command to check everything at once**

```bash
echo "Python: $(python3.12 --version 2>/dev/null || echo 'NOT INSTALLED')"
echo "Node:   $(node --version 2>/dev/null || echo 'NOT INSTALLED')"
echo "Docker: $(docker --version 2>/dev/null || echo 'NOT INSTALLED')"
```

**If you don't want to use MySQL in terminal then install MySQL Workbench**

Install:

- Windows/Mac: download at https://dev.mysql.com/downloads/workbench/ → run the installer → keep default options
- Linux (Ubuntu/Debian): Software Center → search "MySQL Workbench" → Install
- Linux (Arch/CachyOS): Software Center (Discover/Pamac) → search "mysql-workbench" → Install

Connect to your Docker MySQL

Since your MySQL is running inside Docker (from _docker compose up -d mysql_), it's still reachable at _localhost:3306_ — Workbench connects to it exactly like a normal MySQL server.

1. Open MySQL Workbench
2. Click the "+" next to "MySQL Connections"
3. Fill in:

- Connection Name: AI Invoice Accounting
- Hostname: 127.0.0.1
- Port: 3306
- Username: app_user (or whatever you set as MYSQL_USER in your .env)

4. Click "Test Connection" → it will ask for the password → enter **app_password** (or your **MYSQL_PASSWORD** value) → check "Save password"
5. Click OK, then double-click the new connection to open it

You'll now see all databases, including ai_invoice_db, with a full table browser, SQL editor, and ER diagram tool — no terminal needed from here on.

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

### Step 3: Run the Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

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
