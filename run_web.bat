@echo off
:: run_web.bat — Lance l'interface Web pour BD Telegram
set SCRIPT_DIR=%~dp0
set VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe

echo ================================================
echo   Démarrage de l'interface Web BD Telegram...
echo   Allez sur http://127.0.0.1:8000
echo ================================================

"%VENV_PYTHON%" web_ui.py
pause
