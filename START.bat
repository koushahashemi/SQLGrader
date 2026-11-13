@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 app.py
    if errorlevel 1 goto failed
    exit /b 0
)
where python >nul 2>nul
if not errorlevel 1 (
    python app.py
    if errorlevel 1 goto failed
    exit /b 0
)
echo Python 3 was not found.
echo Install Python 3.11 or newer from python.org, including Tcl/Tk and IDLE.
echo During installation, enable Add Python to PATH. Then run START.bat again.
pause
exit /b 1
:failed
echo.
echo The app stopped with an error. See the message above.
echo Ensure Python 3.11 or newer is installed with Tcl/Tk support.
pause
exit /b 1
