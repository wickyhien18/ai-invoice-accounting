@echo off
echo ==============================================
echo KHOI CHAY HE THONG AI INVOICE ACCOUNTING
echo ==============================================

echo [1/5] Dang khoi dong Docker MySQL...
docker compose up -d mysql

echo [2/5] Dang mo Visual Studio Code...
start "" code .

echo [3/5] Dang khoi dong Backend (Port 8000)...
start "Backend FastAPI (8000)" cmd /k "cd backend && .\venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"

echo [4/5] Dang khoi dong AI Service (Port 8001)...
start "AI Service (8001)" cmd /k "cd ai-service && .\venv\Scripts\activate && uvicorn app.main:app --reload --port 8001"

echo [5/5] Dang khoi dong Frontend (Port 5173)...
start "Frontend Vite (5173)" cmd /k "cd frontend && npm run dev"

exit