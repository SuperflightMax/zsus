@echo off
python -m venv .venv
if exist .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
) else (
  echo Failed to create virtual environment
  exit /b 1
)
python -m src.interfaces.cli.main
