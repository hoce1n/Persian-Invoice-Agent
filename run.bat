@echo off
setlocal

cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

echo Starting Persian Invoice Agent on http://127.0.0.1:8001
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

endlocal
