# PowerShell script to run the FastAPI server
Set-Location C:\Users\ventu\BoxCostPro\BoxCostPython
& .\venv\Scripts\Activate.ps1
$env:PYTHONPATH = "C:\Users\ventu\BoxCostPro\BoxCostPython"
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
