@echo off
echo ==============================================
echo BOM DU LIEU HOA DON MOCK (INJECT DATA)
echo ==============================================

cd backend
call .\venv\Scripts\activate
python scripts\inject.py

echo.
echo ==============================================
echo HOAN THANH BOM DU LIEU MOCK!
echo ==============================================
pause