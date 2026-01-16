@echo off
cd /d C:\Users\ventu\BoxCostPro\BoxCostPython
call venv\Scripts\activate.bat
set PYTHONPATH=%CD%
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
pause
