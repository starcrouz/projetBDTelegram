@echo off
:: install_task.bat — Crée une tâche planifiée Windows (dimanche 8h00)
:: Utilise le Python du venv du projet
:: Exécuter en tant qu'Administrateur si nécessaire

set SCRIPT_DIR=%~dp0
set TASK_NAME=BD Telegram Downloader
set VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe

echo.
echo ================================================
echo   Installation de la tâche planifiée Windows
echo   Nom    : %TASK_NAME%
echo   Heure  : Dimanche à 08h00
echo   Python : %VENV_PYTHON%
echo   Script : %SCRIPT_DIR%main.py
echo ================================================
echo.

:: Supprimer l'ancienne tâche si elle existe
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

:: Créer la nouvelle tâche avec le venv Python
schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "\"%VENV_PYTHON%\" \"%SCRIPT_DIR%main.py\"" ^
  /sc WEEKLY ^
  /d SUN ^
  /st 08:00 ^
  /sd 01/01/2025 ^
  /ru "%USERNAME%" ^
  /f

if %errorlevel% == 0 (
    echo.
    echo [OK] Tâche planifiée créée avec succès !
    echo      Le script se lancera chaque dimanche à 08h00.
    echo.
    echo Pour vérifier : Planificateur de tâches Windows ^> Bibliothèque ^> "%TASK_NAME%"
) else (
    echo.
    echo [ERREUR] La création de la tâche a échoué.
    echo          Essayez d'exécuter ce fichier en tant qu'Administrateur.
)

echo.
pause
