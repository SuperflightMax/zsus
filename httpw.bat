@echo off
if exist .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
) else (
  echo Missing .venv. Run boot.sh or create a virtual environment.
  exit /b 1
)
start "" http://localhost:8123
python -m src.interfaces.http.server
