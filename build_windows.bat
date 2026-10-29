@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_windows.ps1"
if errorlevel 1 (
  echo.
  echo Build failed. Check the error above.
) else (
  echo.
  echo EXE ready: dist\SRT-UTF8-Studio.exe
)
pause
