@echo off
echo ===================================
echo  AI Agent Penerjemah Arab-Indonesia
echo ===================================
cd /d D:\PROJECT_APP\agent-arab
call venv\Scripts\activate
echo Memulai server...
start /B uvicorn src.gateway.server:app --host 127.0.0.1 --port 8766 --reload
timeout /t 3 /nobreak > nul
echo Server berjalan di http://127.0.0.1:8766
start http://127.0.0.1:8766
echo.
echo Tekan tombol apa saja untuk menutup jendela ini.
echo (Server tetap berjalan di background)
pause > nul
