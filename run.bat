@echo off
echo.
echo  ^| ^| ^|  ^| ^| ^|^|   ^| ^| ^|^|   ^| ^|^^^^  ^|  ^|^^^|^|  ^|^^^|^|
echo  ^| ^|^|^ ^|^| ^|^|   ^| ^| ^|^|   ^| ^|^^  ^|^|^ ^|^|^^^   ^|^|^^^
echo  ^|^|^|^|^|^|^   ^| ^|   ^| ^| ^|^|   ^| ^|^|^|^|^  ^|^|^|^|^|   ^|^|^|^|^|
echo  ^| ^^^       ^|^|^|^|^^  ^|^|^|^|^|^ ^|^|^^  ^|^|^ ^|^|^^^   ^|^|^^^
echo  ^|           ^^^    ^^^   ^| ^|  ^|^|^ ^|^|^|^|^|   ^|^|^|^|^|
echo.
echo          v1.0.0  --  Personal AI Agent
echo  ================================================
echo.
cd /d D:\PROJECT_APP\Kyuraa
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [WARN] Virtual environment tidak ditemukan, lanjut tanpa aktivasi...
)
echo Memulai server...
timeout /t 1 /nobreak > nul
start /w "" cmd /c "start http://127.0.0.1:8766"
uvicorn src.gateway.server:app --host 127.0.0.1 --port 8766 --reload
