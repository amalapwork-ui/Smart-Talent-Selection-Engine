@echo off
echo ========================================
echo   Smart Talent Selection Engine
echo   Starting Django Backend...
echo ========================================

cd /d %~dp0backend

:: Check for virtual environment
if not exist ".venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt --quiet

echo Running migrations...
python manage.py makemigrations
python manage.py migrate

echo Creating superuser (if not exists)...
python manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); U.objects.filter(username='admin').exists() or U.objects.create_superuser('admin','admin@example.com','admin123')" 2>nul

echo Starting Django server on http://localhost:8000
python manage.py runserver 0.0.0.0:8000
