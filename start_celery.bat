@echo off
echo ========================================
echo   Starting Celery Worker...
echo ========================================

cd /d %~dp0backend

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    call .venv\Scripts\activate.bat
)

echo Broker: django:// (SQLite-based, no Redis needed)
echo Pool:   solo (required on Windows)
celery -A config worker --loglevel=info --pool=solo --concurrency=1
