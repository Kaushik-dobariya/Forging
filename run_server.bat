@echo off
cd /d "%~dp0"
title Forging CMS Dev Server
echo ============================================================
echo Starting Industrial Forging CMS Platform
echo Admin Login:  http://127.0.0.1:8000/admin/login
echo Public Site:  http://127.0.0.1:8000
echo Credentials:  admin@forgingcms.com / Admin@123456
echo ============================================================
set DISABLE_SQLALCHEMY_CEXT=1
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    python main.py
)
pause
