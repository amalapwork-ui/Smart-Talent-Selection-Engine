@echo off
echo ========================================
echo   Smart Talent Selection Engine
echo   Starting React Frontend (Vite)...
echo ========================================

cd /d %~dp0frontend

if not exist "node_modules" (
    echo Installing npm packages...
    npm install
)

echo Starting Vite dev server on http://localhost:3000
npm run dev
