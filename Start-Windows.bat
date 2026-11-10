@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  python bootstrap.py
) else (
  py -3 bootstrap.py
)
if errorlevel 1 (
  echo Install Python 3.12 or newer from https://www.python.org/downloads/ if Python was not found.
  pause
)
