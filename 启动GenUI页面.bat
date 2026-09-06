@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "GENUI_URL=http://127.0.0.1:8765/"
set "GENUI_NO_BROWSER=%~1"

call :CHECK_SERVICE
if not errorlevel 1 goto OPEN_PAGE

where.exe python >nul 2>&1
if errorlevel 1 goto NO_PYTHON
for /f "delims=" %%P in ('where.exe python') do if not defined GENUI_PYTHON set "GENUI_PYTHON=%%P"
set "GENUI_PYTHONW=%GENUI_PYTHON:python.exe=pythonw.exe%"

echo [GenUI] Starting local server...
if exist "%GENUI_PYTHONW%" (
    start "GenUI Workbench" /min "%GENUI_PYTHONW%" -m genui_intent.workbench
) else (
    start "GenUI Workbench" /min "%GENUI_PYTHON%" -m genui_intent.workbench
)
if errorlevel 1 goto START_FAILED

for /l %%I in (1,1,20) do (
    ping.exe 127.0.0.1 -n 2 >nul
    call :CHECK_SERVICE
    if not errorlevel 1 goto OPEN_PAGE
)
goto SERVER_TIMEOUT

:OPEN_PAGE
echo [GenUI] Ready: %GENUI_URL%
if /i "%GENUI_NO_BROWSER%"=="--no-browser" exit /b 0
echo [GenUI] Opening the default browser...
start "" "%GENUI_URL%"
echo.
echo If the browser did not open, copy this address manually:
echo %GENUI_URL%
echo.
echo Press any key to close this window.
pause
exit /b 0

:CHECK_SERVICE
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "try { $r=Invoke-WebRequest -UseBasicParsing -Uri '%GENUI_URL%' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 }; exit 1 } catch { exit 1 }" >nul 2>&1
exit /b %errorlevel%

:NO_PYTHON
echo [GenUI] Python was not found. Install Python 3.10+ and add it to PATH.
pause
exit /b 1

:START_FAILED
echo [GenUI] Failed to create the Python server process.
pause
exit /b 1

:SERVER_TIMEOUT
echo [GenUI] Server was not ready within 20 seconds.
echo Error log: %~dp0genui-server-error.log
if exist "%~dp0genui-server-error.log" type "%~dp0genui-server-error.log"
pause
exit /b 1
