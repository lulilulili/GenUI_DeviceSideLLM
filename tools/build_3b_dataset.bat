@echo off
setlocal
cd /d "%~dp0.."
set PYTHONPATH=%CD%
python tools\build_3b_dataset.py %*
if errorlevel 1 pause
