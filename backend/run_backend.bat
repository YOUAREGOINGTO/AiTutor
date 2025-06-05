@echo off
REM This script activates the venv and runs Uvicorn.
REM It expects to be called from the main launcher.

set VENV_ACTIVATE_SCRIPT="C:\Users\yaswa\OneDrive\Desktop\Local Host\Ai-Tutor\backend\venv\Scripts\activate.bat"
set BACKEND_DIR="C:\Users\yaswa\OneDrive\Desktop\Local Host\Ai-Tutor\backend"
set UVICORN_EXE="C:\Users\yaswa\OneDrive\Desktop\Local Host\Ai-Tutor\backend\venv\Scripts\uvicorn.exe"
@REM set VENV_ACTIVATE_SCRIPT="Look in the venv file its in Bat Format. Look at above example"
@REM set BACKEND_DIR="Backend repository look above for reference"
@REM set UVICORN_EXE="file format uvicorn.exe look in venv and see above for reference"

REM Activate venv
call %VENV_ACTIVATE_SCRIPT%
if %errorlevel% neq 0 (
  echo ERROR: Failed to activate venv using %VENV_ACTIVATE_SCRIPT%
  pause
  exit /b 1
)

REM Change to the correct directory
cd /d %BACKEND_DIR%
if %errorlevel% neq 0 (
  echo ERROR: Failed to change directory to %BACKEND_DIR%
  pause
  exit /b 1
)

REM Echo the command we are about to run for debugging
echo Running: %UVICORN_EXE% --reload --port 8001 tutor_project.asgi:application
echo.

REM Run Uvicorn with explicit path and correct argument order
%UVICORN_EXE% --reload --port 8001 tutor_project.asgi:application

REM Keep window open if uvicorn exits unexpectedly
pause