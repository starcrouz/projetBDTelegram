@echo off
:: run.bat — Lance le script avec le venv
:: Double-cliquer sur ce fichier ou l'appeler depuis une invite de commandes

cd /d "%~dp0"
call venv\Scripts\activate.bat
python main.py %*
