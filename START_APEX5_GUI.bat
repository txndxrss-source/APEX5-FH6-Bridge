@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0APEX5_FH6_GUI.exe" (
    start "" "%~dp0APEX5_FH6_GUI.exe"
    exit /b 0
)

where pythonw.exe >nul 2>&1
if errorlevel 1 (
    where pyw.exe >nul 2>&1
    if errorlevel 1 (
        echo Python was not found.
        echo Install Python 3.10+ and make sure pythonw.exe or pyw.exe is available.
        pause
        exit /b 1
    )
    start "" pyw.exe "%~dp0apex5_gui.pyw"
    exit /b 0
)

start "" pythonw.exe "%~dp0apex5_gui.pyw"
exit /b 0
