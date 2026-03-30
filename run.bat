@echo off
echo ===================================
echo  AI Agent Penerjemah Arab-Indonesia
echo ===================================
cd /d C:\agent-arab
call venv\Scripts\activate
echo Memulai server...
start /B uvicorn src.gateway.server:app --host 127.0.0.1 --port 8765
timeout /t 2 /nobreak > nul
echo Server berjalan di http://localhost:8765
start http://localhost:8765
echo Tekan Ctrl+C di terminal untuk menghentikan agent.
pause
