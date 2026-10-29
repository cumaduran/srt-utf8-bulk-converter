@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (set "PY=py -3") else (set "PY=python")
%PY% -m pip install -r requirements.txt || (pause & exit /b 1)
%PY% app.py
