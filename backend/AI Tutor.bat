@echo off
echo Starting AI Tutor Development Environment...
echo.

REM --- Define Paths ---
@REM set BACKEND_DIR="C:\Users\yaswa\OneDrive\Desktop\Local Host\Ai-Tutor\backend"
@REM set FRONTEND_DIR="C:\Users\yaswa\OneDrive\Desktop\Local Host\Ai-Tutor\frontend"
set BACKEND_DIR="Use Your Backend Repository ends with /backend"
set FRONTEND_DIR="Use Your Frontend Repository ends with /frontend"
set DESKTOP_DIR="%USERPROFILE%\Desktop"

REM --- Define path to the backend runner script ---
set BACKEND_RUNNER_SCRIPT=%BACKEND_DIR%\run_backend.bat

REM --- Validate Paths ---
if not exist %BACKEND_RUNNER_SCRIPT% (
    echo ERROR: Cannot find the backend runner script at: %BACKEND_RUNNER_SCRIPT%
    echo Please ensure run_backend.bat exists in %BACKEND_DIR%
    pause
    exit /b 1
)
if not exist %FRONTEND_DIR%\package.json (
    echo ERROR: Cannot find package.json in %FRONTEND_DIR%
    echo Please check the FRONTEND_DIR path.
    pause
    exit /b 1
)

REM --- Start Django Backend using the dedicated runner script ---
echo Starting Django backend via run_backend.bat (Uvicorn on port 8001)...
REM Use 'call' inside cmd /k to execute the other batch file
start "Django Backend (Uvicorn 8001)" cmd /k "call %BACKEND_RUNNER_SCRIPT%"

REM --- Start React Frontend ---
echo Starting React frontend on port 3001...
echo (Make sure package.json script includes '--port 3001')
cd /d %FRONTEND_DIR%
 if %errorlevel% neq 0 (
  echo ERROR: Failed to change directory to %FRONTEND_DIR%
  pause
  exit /b 1
 )
start "React Frontend (Port 3001)" cmd /k "npm run dev"

REM --- Navigate back to Desktop ---
cd /d %DESKTOP_DIR%

REM --- Wait for Servers ---
echo.
echo Waiting a few seconds for servers to initialize...
timeout /t 8 /nobreak > nul

REM --- Open Browser ---
echo Opening frontend (http://localhost:3001) in your browser...
start http://localhost:3001

echo.
echo --- AI Tutor Launched! ---
echo.
echo - Django backend (Uvicorn) should be running in its own window on port 8001.
echo   (Look for messages like 'Uvicorn running on http://127.0.0.1:8001')
echo - React frontend should be running in its own window on port 3001.
echo - Your browser should have opened to the frontend.
echo.
echo >> To STOP the servers, close the individual 'Django Backend' and 'React Frontend' command windows. <<
echo.

REM Optional: uncomment the line below if you want this main window to stay open until you press a key.
REM pause