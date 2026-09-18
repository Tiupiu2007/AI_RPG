@echo off
cd /d "%~dp0"
where python >nul 2>nul || (echo Python non trovato. Installa Python 3.11+ e riprova.&pause&exit /b 1)
python -m pip install -r requirements.txt
start "AI RPG Browser" http://127.0.0.1:8000/chat.html
python server.py
pause
