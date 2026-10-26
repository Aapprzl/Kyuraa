@echo off
cd /d %~dp0
call venv\Scripts\activate.bat
echo Membebaskan port 8766...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8766 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul
uvicorn src.gateway.server:app --host 127.0.0.1 --port 8766
pause
